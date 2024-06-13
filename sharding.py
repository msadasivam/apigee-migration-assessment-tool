#!/usr/bin/python

# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

import os
import utils
import unifier
import os
import zipfile
from base_logger import logger


def qualification_report_info(each_proxy_dict):
    report = {}

    report['policies'] = {}
    report['JsonPathEnabled'] = {}
    report['AntiPatternQuota'] = {}
    report['CacheWithoutExpiry'] = {}
    for policy, value in each_proxy_dict['Policies'].items():

        # JSONPath Enabled
        if list(value.keys())[0] == 'ExtractVariables':
            report['JsonPathEnabled'][policy] = len(
                value['ExtractVariables'].get('JSONPayload', {}).get('Variable', {}))

        # Quota Policy Anti Pattern
        if list(value.keys())[0] == 'Quota':
            if value['Quota']['Distributed'] == 'false' or value['Quota']['Synchronous'] == 'true':
                report['AntiPatternQuota'][policy] = {}
                report['AntiPatternQuota'][policy]['distributed'] = value['Quota'].get('Distributed', None)
                report['AntiPatternQuota'][policy]['Synchronous'] = value['Quota'].get('Synchronous', None)

        # Unsupported Policies
        Unsupported_policies = ['OAuthV1', 'ConcurrentRatelimit', 'ConnectorCallout',
                                'StatisticsCollector', 'DeleteOAuthV1Info', 'GetOAuthV1Info', 'Ldap']
        if list(value.keys())[0] in Unsupported_policies:
            report['policies'][policy] = list(value.keys())[0]

        # Cache without expiry
        if list(value.keys())[0] == 'PopulateCache' or list(value.keys())[0] == 'ResponseCache':
            if not value[list(value.keys())[0]].get('ExpirySettings'):
                report['CacheWithoutExpiry'][policy] = list(value.keys())[0]

    # api with multiple basepaths
    base_paths = []
    for proxy_endpoint, value in each_proxy_dict['ProxyEndpoints'].items():
        basepath = value['ProxyEndpoint']['HTTPProxyConnection']['BasePath']
        base_paths.append(basepath)
    report['base_paths'] = base_paths

    return report


def unzip_all_bundles(input_cfg):

    export_dir_name = input_cfg.get('export', 'EXPORT_DIR')
    target_dir = input_cfg.get('inputs', 'TARGET_DIR')

    backend_cfg = utils.parse_config('backend.properties')
    source_unzipped_apis = backend_cfg.get('unifier', 'source_unzipped_apis')

    extension = ".zip"
    current_dir = os.getcwd()
    unzip_dir_name = current_dir+'/'+target_dir + \
        '/'+export_dir_name+source_unzipped_apis

    if not os.path.isdir(unzip_dir_name):
        os.makedirs(unzip_dir_name)  # create unzip directory

    # change directory from working dir to dir with files
    os.chdir('./'+target_dir+'/'+export_dir_name+'/apis')
    for item in os.listdir('./'):  # loop through items in dir

        if item.endswith(extension):  # check for ".zip" extension

            file_name = os.path.abspath(item)  # get full path of files

            zip_ref = zipfile.ZipFile(file_name)  # create zipfile object

            # extract file to dir
            zip_ref.extractall(f"../{source_unzipped_apis}/{item[:-4]}/")
            zip_ref.close()  # close file

    os.chdir(current_dir)  # revert to current directory


def proxy_dependency_map(cfg, exportData):

    unzip_all_bundles(cfg)

    input_cfg = utils.parse_config('input.properties')
    export_dir_name = input_cfg.get('export', 'EXPORT_DIR')
    target_dir = input_cfg.get('inputs', 'TARGET_DIR')

    backend_cfg = utils.parse_config('backend.properties')
    source_unzipped_apis = backend_cfg.get('unifier', 'source_unzipped_apis')

    current_dir = os.getcwd()
    apis_dirs = current_dir+'/'+target_dir+'/'+export_dir_name+source_unzipped_apis

    result = dict()
    proxy_dir = apis_dirs
    proxyDependencyMap = dict()
    args = ((apiname, proxy_dir, proxyDependencyMap)
            for apiname in exportData["orgConfig"]["apis"].keys())

    result = utils.run_parallel(proxy_dependency_map_parallel, args)
    res = dict()
    for item in result:
        for key, value in item.items():
            res[key] = value

    return res


def proxy_dependency_map_parallel(arg_tuple):
    try:
        each_dir = arg_tuple[0]
        proxy_dir = arg_tuple[1]
        proxyDependencyMap = arg_tuple[2]
        logger.info(f"processing {each_dir}")
        each_proxy_dict = utils.read_proxy_artifacts(
            f"{proxy_dir}/{each_dir}/apiproxy",
            utils.parse_proxy_root_sharding(
                f"{proxy_dir}/{each_dir}/apiproxy")
        )

        each_proxy_rel = utils.get_proxy_objects_relationships(each_proxy_dict)
        proxyDependencyMap[each_dir] = dict()

        # checking if the pe > count_provided
        cfg = utils.parse_config('backend.properties')
        proxy_endpoint_cnt = utils.get_proxy_endpoint_count(cfg)
        input_cfg = utils.parse_config('input.properties')
        export_dir_name = input_cfg.get('export', 'EXPORT_DIR')
        target_dir = input_cfg.get('inputs', 'TARGET_DIR')
        unifier_output_dir = cfg.get('unifier', 'unifier_output_dir')

        if len(each_proxy_rel.keys()) > proxy_endpoint_cnt:

            proxy_split_result = unifier.proxy_unifier(each_dir)
            proxyDependencyMap[each_dir]["is_split"] = True
            proxyDependencyMap[each_dir]["split_output_names"] = list()
            for dir_name, each_proxy_split in proxy_split_result.items():
                proxyDependencyMap[dir_name] = dict()
                proxy_dict = utils.read_proxy_artifacts(
                    f"./{target_dir}/{export_dir_name}/{unifier_output_dir}/{dir_name}/apiproxy",
                    utils.parse_proxy_root_sharding(
                        f"./{target_dir}/{export_dir_name}/{unifier_output_dir}/{dir_name}/apiproxy")
                )

                proxy_rel = utils.get_proxy_objects_relationships(proxy_dict)
                proxyDependencyMap = build_proxy_dependency(
                    proxyDependencyMap, proxy_rel, proxy_dict, dir_name)
                proxyDependencyMap[dir_name]["qualification"] = qualification_report_info(
                    proxy_dict)
                proxyDependencyMap[dir_name]["unifier_created"] = True
                proxyDependencyMap[each_dir]["split_output_names"].append(
                    dir_name)
        else:
            proxyDependencyMap = build_proxy_dependency(
                proxyDependencyMap, each_proxy_rel, each_proxy_dict, each_dir)
        proxyDependencyMap[each_dir]["qualification"] = qualification_report_info(
            each_proxy_dict)

    except Exception as error:
        logger.error(
            f"Error in proxy dependency map parallel function. ERROR-INFO - {error} {each_dir}")
    finally:
        return proxyDependencyMap


def build_proxy_dependency(proxyDependencyMap, each_proxy_rel, each_proxy_dict, each_dir):
    for proxyname, values in each_proxy_rel.items():
        if each_proxy_rel[proxyname].get('Policies') is not None:
            for eachpolicy in each_proxy_rel[proxyname]['Policies']:
                if "FlowCallout" in list(each_proxy_dict['Policies'][eachpolicy].keys()):
                    if "SharedFlowBundle" in each_proxy_dict['Policies'][eachpolicy]["FlowCallout"]:
                        if not proxyDependencyMap[each_dir].get('SharedFlow'):
                            proxyDependencyMap[each_dir]['SharedFlow'] = [
                                each_proxy_dict['Policies'][eachpolicy]["FlowCallout"]["SharedFlowBundle"]]
                        else:
                            proxyDependencyMap[each_dir]['SharedFlow'].append(
                                each_proxy_dict['Policies'][eachpolicy]["FlowCallout"]["SharedFlowBundle"])

                if "KeyValueMapOperations" in list(each_proxy_dict['Policies'][eachpolicy].keys()):
                    kvmname = each_proxy_dict['Policies'][eachpolicy]['KeyValueMapOperations'].get(
                        '@mapIdentifier')
                    if not proxyDependencyMap[each_dir].get('KVM'):
                        proxyDependencyMap[each_dir]['KVM'] = [kvmname]
                    else:
                        proxyDependencyMap[each_dir]['KVM'].append(kvmname)

        if each_proxy_rel[proxyname].get('TargetEndpoints') is not None:
            for eachtargetendpoint in each_proxy_rel[proxyname]['TargetEndpoints']:
                if 'HostedTarget' in each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint'].keys():
                    return proxyDependencyMap
                targetservers = each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint']['HTTPTargetConnection'].get(
                    'LoadBalancer')
                if targetservers is not None:
                    if isinstance(targetservers.get('Server'), dict):
                        if not proxyDependencyMap[each_dir].get("TargetServer"):
                            proxyDependencyMap[each_dir]["TargetServer"] = [
                                targetservers.get('@name')]
                        else:
                            proxyDependencyMap[each_dir]["TargetServer"].append(
                                targetservers.get('@name'))
                    else:
                        for targetdict in targetservers.get('Server'):
                            if not proxyDependencyMap[each_dir].get("TargetServer"):
                                proxyDependencyMap[each_dir]["TargetServer"] = [
                                    targetdict.get('@name')]
                            else:
                                proxyDependencyMap[each_dir]["TargetServer"].append(
                                    targetdict.get('@name'))
                else:
                    if each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint']['HTTPTargetConnection'].get('SSLInfo'):
                        sslinfo = each_proxy_dict['TargetEndpoints'][eachtargetendpoint]['TargetEndpoint']['HTTPTargetConnection'].get(
                            'SSLInfo')
                        if not proxyDependencyMap[each_dir].get("References"):
                            proxyDependencyMap[each_dir]["References"] = [
                                {"Keystore": sslinfo.get('KeyStore'), "Trustore": sslinfo.get('TrustStore')}]
                        else:
                            proxyDependencyMap[each_dir]["References"].append(
                                {"Keystore": sslinfo.get('KeyStore'), "Trustore": sslinfo.get('TrustStore')})

    return proxyDependencyMap


def sharding_wrapper(proxyDependencyMap, exportData):

    shard_result = dict()

    for env, values in exportData["envConfig"].items():
        result_dict = dict()
        for apiname in values["apis"].keys():

            if proxyDependencyMap[apiname].get("is_split") != True:
                result_dict[apiname] = proxyDependencyMap[apiname]
            else:
                for splits in proxyDependencyMap[apiname]["split_output_names"]:
                    result_dict[splits] = proxyDependencyMap[splits]

        result = environment_sharding(env, result_dict)
        shard_result[env] = result[0]
        shard_result[env]["not_processed_apis"] = result[1]

    return shard_result


def environment_sharding(env, proxyDependencyMap):

    # sort proxyDependencyMap in alphabetically order
    myKeys = list(proxyDependencyMap.keys())
    myKeys.sort()
    sorted_dict = {i: proxyDependencyMap[i] for i in myKeys}

    proxyDependencyMap = dict()
    proxyDependencyMap = sorted_dict

    cfg = utils.parse_config('backend.properties')
    per_env_proxy_limit = cfg.getint('inputs', 'NO_OF_PROXIES_PER_ENV_LIMITS')
    total_units_per_envn = cfg.getint(
        'inputs', 'NO_OF_PROXIES_AND_SHARED_FLOWS_PER_ENV_LIMITS')

    env_name = env
    env_slot = dict()
    slot_cntr = 1
    notprocessed = dict()
    for apiname, dependencies in proxyDependencyMap.copy().items():
        if dependencies.get("SharedFlow") and len(dependencies.get("SharedFlow")) > (total_units_per_envn-1):
            notprocessed[apiname] = dependencies
            del proxyDependencyMap[apiname]

    while proxyDependencyMap:

        if not env_slot or not env_slot.get(env_name+str(slot_cntr)):
            env_slot[env_name+str(slot_cntr)] = dict(
                {"proxyname": [], "shared_flow": [], "target_server": []})

        # check total proxies in a slot
        if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) >= per_env_proxy_limit or (len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(env_slot[env_name+str(slot_cntr)]["shared_flow"]) >= total_units_per_envn):
            slot_cntr = slot_cntr + 1
            env_slot[env_name+str(slot_cntr)] = dict(
                {"proxyname": [], "shared_flow": [], "target_server": []})

        # add proxies and sharedflow provided sum of it <= than 60
        for apiname, dependencies in proxyDependencyMap.copy().items():
            if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):

                # add proxy name
                env_slot[env_name+str(slot_cntr)]["proxyname"].append(apiname)

                # add unique shared flows

                unique_shared_flow = find_unique_items(
                    env_slot[env_name+str(slot_cntr)]["shared_flow"], dependencies.get("SharedFlow"))
                if unique_shared_flow:
                    env_slot[env_name+str(slot_cntr)]["shared_flow"].clear()
                    env_slot[env_name+str(slot_cntr)
                             ]["shared_flow"].extend(unique_shared_flow)

                # add unique target servers
                unique_target_server = find_unique_items(
                    env_slot[env_name+str(slot_cntr)]["target_server"], dependencies.get("TargetServer"))
                if unique_target_server:
                    env_slot[env_name+str(slot_cntr)]["target_server"].clear()
                    env_slot[env_name+str(slot_cntr)
                             ]["target_server"].extend(unique_target_server)

                # remove proxy from proxy dependency map
                del proxyDependencyMap[apiname]

        # add proxies that have same sharedflow
        for apiname, dependencies in proxyDependencyMap.copy().items():

            if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):

                if is_subset(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)].get("shared_flow")):
                    # add proxy name
                    env_slot[env_name+str(slot_cntr)
                             ]["proxyname"].append(apiname)

                    # add unique target servers
                    if dependencies.get("TargetServer"):
                        unique_target_server = find_unique_items(
                            env_slot[env_name+str(slot_cntr)]["target_server"], dependencies.get("TargetServer"))
                        env_slot[env_name+str(slot_cntr)
                                 ]["target_server"].clear()
                        env_slot[env_name+str(slot_cntr)
                                 ]["target_server"].extend(unique_target_server)

                    # remove proxy from proxy dependency map
                    del proxyDependencyMap[apiname]

        # add proxies that do not have sharedflow but share same target servers
        for apiname, dependencies in proxyDependencyMap.copy().items():

            if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):

                if not dependencies.get('SharedFlow') and is_subset(dependencies.get("TargetServer"), env_slot[env_name+str(slot_cntr)].get("target_server")):
                    # add proxy name
                    env_slot[env_name+str(slot_cntr)
                             ]["proxyname"].append(apiname)

                    # remove from proxy dependency map
                    del proxyDependencyMap[apiname]

        # add proxies that do not have any shareflow and target servers
        for apiname, dependencies in proxyDependencyMap.copy().items():
            if not dependencies.get("SharedFlow") and not dependencies.get("TargetServer"):

                if len(env_slot[env_name+str(slot_cntr)]["proxyname"]) < per_env_proxy_limit and ((len(env_slot[env_name+str(slot_cntr)]["proxyname"]) + len(find_unique_items(dependencies.get("SharedFlow"), env_slot[env_name+str(slot_cntr)]["shared_flow"]))) < total_units_per_envn):
                    # add proxy name
                    env_slot[env_name+str(slot_cntr)
                             ]["proxyname"].append(apiname)

                    # remove from proxy dependency map
                    del proxyDependencyMap[apiname]

        slot_cntr = slot_cntr+1
    return [env_slot, notprocessed]


def find_unique_items(list1, list2):
    if list1 and list2:
        unique_items = set(list1) | set(list2)
        return unique_items
    elif list1:
        return list1
    else:
        return list2


def is_subset(list1, list2):
    """Returns True if list1 is a subset of list2, False otherwise."""
    if not list1 or not list2:
        return True

    for item in list1:
        if item not in list2:
            return False

    return True
