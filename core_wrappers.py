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

from exporter import ApigeeExporter
from validator import ApigeeValidator
from qualification_report import QualificationReport
from topology import ApigeeTopology
from utils import *
from pyvis.network import Network
import networkx as nx
import sharding
from base_logger import logger

seperator = ' | '
DEFAULT_GCP_ENV_TYPE = 'BASE'


def export_artifacts(cfg, resources_list):
    SOURCE_URL = cfg.get('inputs', 'SOURCE_URL')
    SOURCE_ORG = cfg.get('inputs', 'SOURCE_ORG')
    SOURCE_AUTH_TOKEN = get_source_auth_token()
    SOURCE_AUTH_TYPE = cfg.get('inputs', 'SOURCE_AUTH_TYPE')
    TARGET_DIR = cfg.get('inputs', 'TARGET_DIR')
    EXPORT_DIR = f"{TARGET_DIR}/{cfg.get('export','EXPORT_DIR')}"
    API_EXPORT_DIR = f"{EXPORT_DIR}/apis"
    SF_EXPORT_DIR = f"{EXPORT_DIR}/sharedflows"
    create_dir(API_EXPORT_DIR)
    create_dir(SF_EXPORT_DIR)
    apigeeExport = ApigeeExporter(
        SOURCE_URL,
        SOURCE_ORG,
        SOURCE_AUTH_TOKEN,
        SOURCE_AUTH_TYPE
    )
    logger.info('------------------- EXPORT -----------------------')
    export_data = apigeeExport.get_export_data(resources_list, EXPORT_DIR)
    logger.debug(export_data)
    apigeeExport.create_export_state(EXPORT_DIR)
    # apigeeExport.export_api_proxy_bundles(EXPORT_DIR)

    proxy_dependency_map = sharding.proxy_dependency_map(cfg, export_data)
    sharding_output = sharding.sharding_wrapper(
        proxy_dependency_map, export_data)

    export_data['proxy_dependency_map'] = proxy_dependency_map
    export_data['sharding_output'] = sharding_output

    return export_data


def validate_artifacts(cfg, export_data):
    logger.info('------------------- VALIDATE -----------------------')
    report = {}
    TARGET_DIR = cfg.get('inputs', 'TARGET_DIR')
    EXPORT_DIR = f"{TARGET_DIR}/{cfg.get('export','EXPORT_DIR')}"
    GCP_PROJECT_ID = cfg.get('inputs', 'GCP_PROJECT_ID')
    GCP_ENV_TYPE = cfg.get('inputs', 'GCP_ENV_TYPE',
                           fallback=DEFAULT_GCP_ENV_TYPE)
    GCP_TOKEN = get_access_token()

    apigeeValidator = ApigeeValidator(GCP_PROJECT_ID, GCP_TOKEN, GCP_ENV_TYPE)

    for env, env_data in export_data['envConfig'].items():
        logger.info(f'Environment -- {env}')
        targetServers = export_data['envConfig'][env]['targetServers']
        resourcefiles = export_data['envConfig'][env]['resourcefiles']
        flowhooks = export_data['envConfig'][env]['flowhooks']
        report[env + seperator +
               'targetServers'] = apigeeValidator.validate_env_targetservers(targetServers)
        report[env + seperator +
               'resourcefiles'] = apigeeValidator.validate_env_resourcefiles(resourcefiles)
        report[env + seperator +
               'flowhooks'] = apigeeValidator.validate_env_flowhooks(env, flowhooks)

    validation = apigeeValidator.validate_proxy_bundles(f"{EXPORT_DIR}/apis")
    # Todo
    # validate proxy unifier output bundles
    report.update(validation)
    report_header = ['Type', 'Name', 'Importable', 'Reason']
    report_rows = []
    for each_type, type_data in report.items():
        for each_item in type_data:
            report_rows.append(
                [
                    each_type,
                    each_item.get('name', None),
                    each_item.get('importable', None),
                    "" if len(each_item.get('reason', [])) == 0 else json.dumps(
                        each_item.get('reason', []), indent=2)
                ]
            )

    CSV_REPORT = cfg.get('validate', 'CSV_REPORT')
    write_csv_report(f'{TARGET_DIR}/{CSV_REPORT}', report_header, report_rows)
    return report


def visualize_artifacts(cfg, export_data, report):
    logger.info('------------------- VISUALIZE -----------------------')
    SOURCE_ORG = cfg.get('inputs', 'SOURCE_ORG')
    SOURCE_UI_URL = cfg.get('inputs', 'SOURCE_UI_URL')
    API_URL = cfg.get('inputs', 'API_URL')
    # API_URL = "https://apidocs.apigee.com/docs"
    exportorg = export_data['orgConfig']
    exportenv = export_data['envConfig']
    G = nx.DiGraph()

    # Process the report
    final_report = {}
    for res, val in report.items():
        final_report[res] = {}
        for i in val:
            if (i['importable']):
                final_report[res][i['name']] = i['importable']
            else:
                final_report[res][i['name']] = i['reason']

    # Org level resources
    org_url = SOURCE_UI_URL + SOURCE_ORG
    G.add_node('ORG' + seperator + SOURCE_ORG, size=30, color='pink')
    G.nodes['ORG' + seperator +
            SOURCE_ORG]['title'] = f'<a href={org_url} target="_blank">Organization - {SOURCE_ORG}</a>'
    for key, value in exportorg.items():
        G.add_edge('ORG' + seperator + key.upper(),
                   'ORG' + seperator + SOURCE_ORG)
        G.nodes['ORG' + seperator + key.upper()]['size'] = 20

        # for titles of key nodes
        if key == 'apiProducts':
            res_url = SOURCE_UI_URL + SOURCE_ORG + '/products'
            G.nodes['ORG' + seperator + key.upper()
                    ]['title'] = f'<a href={res_url} target="_blank">Org level {key}</a>'
        elif key == 'kvms':
            res_url = API_URL + '/key-value-maps/1/overview'
            G.nodes['ORG' + seperator + key.upper()
                    ]['title'] = f'<a href={res_url} target="_blank">Org level {key}</a>'
        else:
            res_url = SOURCE_UI_URL + SOURCE_ORG + '/' + key
            G.nodes['ORG' + seperator + key.upper()
                    ]['title'] = f'<a href={res_url} target="_blank">Org level {key}</a>'

        # check threshold for resources
        threshold = 100
        if len(value) > threshold:
            G.add_edge('More than ' + str(threshold) + ' ' +
                       key, 'ORG' + seperator + key.upper())
            G.nodes['More than ' + str(threshold) +
                    ' ' + key]['color'] = 'black'
            G.nodes['More than ' + str(threshold) + ' ' + key]['size'] = 20
            G.nodes['More than ' + str(threshold) + ' ' +
                    key]['title'] = 'Total - ' + str(len(value)) + ' ' + key
            continue

        for name, val in value.items():
            G.add_edge('ORG' + seperator + name,
                       'ORG' + seperator + key.upper())
            if key == 'apis' or key == 'sharedflows':
                G.nodes['ORG' + seperator +
                        name]['title'] = key[:-1] + ' named ' + name
            else:
                G.nodes['ORG' + seperator + name]['title'] = 'Org level ' + \
                    key[:-1] + ' named ' + name

            # check if importable or not
            if key == 'apis' or key == 'sharedflows':
                if final_report.get(key):
                    if final_report[key][name] != True:
                        G.nodes['ORG' + seperator + name]['color'] = 'red'
                        count = 1
                        viols = ""
                        for violation in final_report[key][name][0]['violations']:
                            viols += str(count) + ". "
                            viols += violation['description'] + " "
                            count = count+1
                        G.nodes['ORG' + seperator +
                                name]['title'] = '<b>Reason</b> : ' + viols

    # Environment level resources
    G.add_edge('ORG' + seperator + 'ENVs', 'ORG' + seperator + SOURCE_ORG)
    G.nodes['ORG' + seperator + 'ENVs']['size'] = 20
    env_url = API_URL + '/environments/1/overview'
    G.nodes['ORG' + seperator +
            'ENVs']['title'] = f'<a href={env_url} target="_blank">Environments</a>'

    for env, value in exportenv.items():
        G.add_edge(env, 'ORG | ENVs')
        G.nodes[env]['title'] = env + ' Environment'
        base_url = SOURCE_UI_URL + SOURCE_ORG + '/environments/' + env + '/'
        for resource, val in value.items():
            G.add_edge(env + seperator + resource.upper(), env)

            # hyperlinks in titles
            if resource == 'resourcefiles':
                res_url = API_URL + '/resource-files/1/overview'
                G.nodes[env + seperator + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'
            elif resource == 'kvms':
                res_url = base_url + 'key-value-maps'
                G.nodes[env + seperator + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'
            elif resource == 'vhosts':
                res_url = base_url + 'virtual-hosts'
                G.nodes[env + seperator + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'
            elif resource == 'targetServers':
                res_url = base_url + 'target-servers'
                G.nodes[env + seperator + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'
            else:
                res_url = base_url + resource
                G.nodes[env + seperator + resource.upper(
                )]['title'] = f'<a href={res_url} target="_blank">Env {env} level {resource}</a>'

            # check threshold for env level resources
            threshold = 100
            if len(val) > threshold:
                G.add_edge('More than ' + str(threshold) + ' ' + resource +
                           ' in env ' + env, env + seperator + resource.upper())
                G.nodes['More than ' + str(threshold) + ' ' +
                        resource + ' in env ' + env]['color'] = 'black'
                G.nodes['More than ' + str(threshold) + ' ' +
                        resource + ' in env ' + env]['size'] = 20
                G.nodes['More than ' + str(threshold) + ' ' + resource + ' in env ' +
                        env]['title'] = 'Total - ' + str(len(val)) + ' ' + resource
                continue

            for name, info in val.items():
                G.add_edge(env + seperator + name, env +
                           seperator + resource.upper())
                G.nodes[env + seperator + name]['title'] = 'Env ' + \
                    env + ' level ' + resource[:-1] + ' named ' + name

                # check if importable or not
                if resource == 'targetServers' or resource == 'resourcefiles':
                    if final_report[env + seperator + resource][name] != True:
                        G.nodes[env + seperator + name]['color'] = 'red'
                        G.nodes[env + seperator + name]['title'] = '<b>Reason</b> : ' + \
                            final_report[env + seperator +
                                         resource][name][0]['error_msg']['message']

    net = Network(notebook=True, cdn_resources='in_line',
                  width=1000, height=800)
    net.from_nx(G)
    TARGET_DIR = cfg.get('inputs', 'TARGET_DIR')
    VISUALIZATION_GRAPH_FILE = cfg.get('visualize', 'VISUALIZATION_GRAPH_FILE')
    net.show(f'{TARGET_DIR}/{VISUALIZATION_GRAPH_FILE}')


def qualification_report(cfg, backend_cfg, export_data, topology_mapping):
    logger.info(
        '------------------- Qualification Report -----------------------')

    TARGET_DIR = cfg.get('inputs', 'TARGET_DIR')
    orgName = cfg.get('inputs', 'SOURCE_ORG')
    QUALIFICATION_REPORT = cfg.get('report', 'QUALIFICATION_REPORT')

    qualificationReport = QualificationReport(
        f'{TARGET_DIR}/{QUALIFICATION_REPORT}',
        export_data,
        topology_mapping,
        cfg,
        backend_cfg,
        orgName
    )

    SOURCE_APIGEE_VERSION = cfg.get('inputs', 'SOURCE_APIGEE_VERSION')

    qualificationReport.sharding()

    if SOURCE_APIGEE_VERSION == 'OPDK':
        qualificationReport.report_network_topology()

    qualificationReport.report_api_with_multiple_basepaths()
    qualificationReport.report_env_limits()
    qualificationReport.report_org_limits()
    qualificationReport.report_api_limits()
    qualificationReport.report_unsupported_policies()
    qualificationReport.report_cname_anomaly()
    qualificationReport.report_json_path_enabled()
    qualificationReport.report_apps_without_api_products()
    qualificationReport.report_cache_without_expiry()
    qualificationReport.report_anti_patterns()
    qualificationReport.report_company_and_developer()
    qualificationReport.report_north_bound_mtls()
    qualificationReport.report_proxies_per_env()
    qualificationReport.report_alias_keycert()
    qualificationReport.sharded_proxies()
    qualificationReport.report_org_resourcefiles()
    qualificationReport.qualification_report_summary()

    qualificationReport.reverse_sheets()

    qualificationReport.close()


def get_topology(cfg):
    logger.info(
        '------------------- Installation Topology -----------------------')

    SOURCE_URL = cfg.get('inputs', 'SOURCE_URL')
    SOURCE_ORG = cfg.get('inputs', 'SOURCE_ORG')
    SOURCE_AUTH_TOKEN = get_source_auth_token()
    SOURCE_AUTH_TYPE = cfg.get('inputs', 'SOURCE_AUTH_TYPE')
    apigeeTopology = ApigeeTopology(
        SOURCE_URL,
        SOURCE_ORG,
        SOURCE_AUTH_TOKEN,
        SOURCE_AUTH_TYPE,
        cfg
    )

    pod_component_mapping = apigeeTopology.get_topology_mapping()

    data_center_mapping = apigeeTopology.get_data_center_mapping(
        pod_component_mapping)

    apigeeTopology.draw_topology_graph_diagram(data_center_mapping)

    topology_json = {
        "pod_component_mapping": pod_component_mapping,
        "data_center_mapping": data_center_mapping
    }
    return topology_json
