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

from classic import ApigeeClassic
from utils import create_dir, run_parallel, write_file, write_json
from base_logger import logger
import os
import json


class ApigeeExporter():

    def __init__(self, baseurl, org, token, auth_type):
        self.baseurl = baseurl
        self.org = org
        self.token = token
        self.auth_type = auth_type
        self.opdk = ApigeeClassic(baseurl, org, token, self.auth_type)
        self.env_object_types = {
            'targetservers': 'targetServers',
            'keyvaluemaps': 'kvms',
            'references': 'references',
            'resourcefiles': 'resourcefiles',
            'keystores': 'keystores',
            'flowhooks': 'flowhooks',
            'caches': 'caches'
        }
        self.org_object_types = {
            'org_keyvaluemaps': 'kvms',
            'developers': 'developers',
            'apiproducts': 'apiProducts',
            'companies': 'companies',
            'apps': 'apps',
            'resourcefiles': 'resourcefiles',
        }
        self.export_data = {
            'orgConfig': {},
            'envConfig': {}
        }

    def export_env(self):
        logger.info("--Exporting environments--")
        envs = self.opdk.list_environments()

        for env in envs:
            self.export_data['envConfig'][env] = {}

    def export_vhosts(self):
        envs = self.export_data['envConfig'].keys()
        for env in envs:
            self.export_data['envConfig'][env]['vhosts'] = {}
            vhosts = self.opdk.list_env_vhosts(env)
            for vhost in vhosts:
                vhost_data = self.opdk.get_env_vhost(env, vhost)
                self.export_data['envConfig'][env]['vhosts'][vhost] = vhost_data

    def export_env_objects(self, env_objects_keys, export_dir):
        for env in self.export_data['envConfig'].keys():
            for each_env_object_type in env_objects_keys:
                env_objects = self.opdk.list_env_objects(
                    env, each_env_object_type)
                if each_env_object_type == 'resourcefiles':
                    logger.info("--Exporting Resourcefiles--")
                    env_objects = env_objects['resourceFile']
                    for each_env_object in env_objects:
                        logger.info(
                            f"Exporting Resourcefile {each_env_object['name']}")
                        create_dir(
                            f"{export_dir}/resourceFiles/{each_env_object['type']}")
                        obj_data = self.opdk.get_env_object(
                            env, each_env_object_type, each_env_object)
                        write_file(
                            f"{export_dir}/resourceFiles/{each_env_object['type']}/{each_env_object['name']}", obj_data)
                        self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]][each_env_object['name']] = {
                            'name': each_env_object['name'],
                            'type': each_env_object['type'],
                            'file': f"{export_dir}/resourceFiles/{each_env_object['type']}/{each_env_object['name']}"
                        }
                elif each_env_object_type == 'keystores':
                    create_dir(f"{export_dir}/keystore_certificates/env-{env}")
                    logger.info("--Exporting keystores--")
                    for each_env_object in env_objects:
                        logger.info(f"Exporting keystore {each_env_object}")
                        create_dir(
                            f"{export_dir}/keystore_certificates/env-{env}/{each_env_object}")
                        obj_data = self.opdk.get_env_object(
                            env, each_env_object_type, each_env_object)
                        obj_data['alias_data'] = {}
                        for alias in obj_data.get('aliases', []):
                            create_dir(
                                f"{export_dir}/keystore_certificates/env-{env}/{each_env_object}/{alias.get('aliasName')}")
                            alias_data = self.opdk.get_env_object(
                                env, f"keystores/{each_env_object}/aliases", alias.get('aliasName'))
                            certificate = self.opdk.get_env_object(
                                env, f"keystores/{each_env_object}/aliases", f"{alias.get('aliasName')}/certificate")
                            with open(f"{export_dir}/keystore_certificates/env-{env}/{each_env_object}/{alias.get('aliasName')}/certificate.pem", "wb") as f:
                                f.write(certificate)
                            obj_data['alias_data'][alias.get(
                                'aliasName')] = alias_data
                        self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]
                                                           ][each_env_object] = obj_data
                else:
                    logger.info(f"--Exporting {each_env_object_type}--")
                    for each_env_object in env_objects:
                        logger.info(
                            f"Exporting {each_env_object_type} {each_env_object}")
                        obj_data = self.opdk.get_env_object(
                            env, each_env_object_type, each_env_object)
                        self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]
                                                           ][each_env_object] = obj_data

    def export_org_objects(self, org_objects_keys):
        for each_org_object_type in org_objects_keys:
            logger.info(f"--Exporting org {each_org_object_type}--")
            self.export_data['orgConfig'][self.org_object_types[each_org_object_type]] = {
            }
            if each_org_object_type == 'org_keyvaluemaps':
                each_org_object_type = 'keyvaluemaps'
            org_objects = self.opdk.list_org_objects(each_org_object_type)

            if each_org_object_type == 'resourcefiles':
                org_objects = org_objects['resourceFile']
                for each_org_object in org_objects:
                    logger.info(
                        f"Exporting {each_org_object_type} {each_org_object}")
                    obj_data = self.opdk.get_org_object(
                        each_org_object_type, each_org_object)
                    self.export_data['orgConfig'][self.org_object_types[each_org_object_type]][each_org_object['name']] = {
                        'name': each_org_object['name'],
                        'type': each_org_object['type']
                    }

            elif each_org_object_type == 'keyvaluemaps':
                for each_org_object in org_objects:
                    logger.info(
                        f"Exporting {each_org_object_type} {each_org_object}")
                    obj_data = self.opdk.get_org_object(
                        each_org_object_type, each_org_object)
                    self.export_data['orgConfig'][self.org_object_types['org_keyvaluemaps']
                                                  ][each_org_object] = obj_data
            else:
                for each_org_object in org_objects:
                    logger.info(
                        f"Exporting {each_org_object_type} {each_org_object}")
                    obj_data = self.opdk.get_org_object(
                        each_org_object_type, each_org_object)
                    self.export_data['orgConfig'][self.org_object_types[each_org_object_type]
                                                  ][each_org_object] = obj_data

    def developers_list(self):
        developers = self.opdk.list_org_objects('developers')
        developers_dict = {}
        for developer in developers:
            developer_data = self.opdk.get_org_object('developers', developer)
            developers_dict[developer_data['developerId']] = developer
        return developers_dict

    def export_api_metadata(self, api_types):
        for each_api_type in api_types:
            logger.info(f"--Exporting {each_api_type} metadata--")
            apis = self.opdk.list_apis(each_api_type)

            for each_api in apis:
                logger.info(f"Exporting {each_api_type} {each_api}")
                # extract revisions
                revs = self.opdk.list_api_revisions(each_api_type, each_api)
                self.export_data['orgConfig'][each_api_type][each_api] = revs

                # extract env level info
                deployments = self.opdk.api_env_mapping(each_api_type, each_api)
                for env in deployments['environment']:
                    env_name = env.get('name')
                    revisions = []
                    for revision in env.get('revision'):
                        revisions.append(revision.get('name'))
                    if self.export_data['envConfig'][env_name].get(each_api_type):
                        self.export_data['envConfig'][env_name][each_api_type][each_api] = revisions
                    else:
                        self.export_data['envConfig'][env_name][each_api_type] = {}
                        self.export_data['envConfig'][env_name][each_api_type][each_api] = revisions

    def export_api_proxy_bundles(self, export_dir, api_types):
        for each_api_type in api_types:
            # apis=self.opdk.list_apis(each_api_type)
            apis = self.export_data['orgConfig'][each_api_type].keys()
            args = (
                (each_api_type, api, f"{export_dir}/{each_api_type}") for api in apis)
            run_parallel(self.opdk.fetch_proxy, args)

    def get_export_data(self, resources_list, export_dir):
        self.export_env()

        for env in self.export_data['envConfig'].keys():
            self.export_data['envConfig'][env]['vhosts'] = {}
            self.export_data['envConfig'][env]['apis'] = {}
            self.export_data['envConfig'][env]['sharedflows'] = {}
            for each_env_object_type in self.env_object_types.keys():
                self.export_data['envConfig'][env][self.env_object_types[each_env_object_type]] = {
                }

        for each_org_object_type in self.org_object_types.keys():
            self.export_data['orgConfig'][self.org_object_types[each_org_object_type]] = {
            }
        self.export_data['orgConfig']['apis'] = {}
        self.export_data['orgConfig']['sharedflows'] = {}

        env_objects = []
        org_objects = []
        api_types = []

        if 'all' in resources_list:
            self.export_vhosts()
            for env_object in self.env_object_types.keys():
                env_objects.append(env_object)

            for org_object in self.org_object_types.keys():
                org_objects.append(org_object)

            api_types = ['apis', 'sharedflows']

        else:
            if 'vhosts' in resources_list:
                self.export_vhosts()

            if 'apis' in resources_list:
                api_types.append('apis')
            if 'sharedflows' in resources_list:
                api_types.append('sharedflows')

            for object in resources_list:
                if object in self.env_object_types.keys():
                    env_objects.append(object)

                if object in self.org_object_types.keys():
                    org_objects.append(object)

        self.export_api_metadata(api_types)
        self.export_api_proxy_bundles(export_dir, api_types)

        if len(env_objects) != 0:
            self.export_env_objects(env_objects, export_dir)
        if len(org_objects) != 0:
            self.export_org_objects(org_objects)

        return self.export_data

    def create_export_state(self, export_dir):
        create_dir(f"{export_dir}/orgConfig")
        create_dir(f"{export_dir}/envConfig")

        for resource, metadata in self.export_data["orgConfig"].items():
            create_dir(f"{export_dir}/orgConfig/{resource}")
            for res_name, res_metadata in metadata.items():
                write_json(
                    f"{export_dir}/orgConfig/{resource}/{res_name}.json", res_metadata)

        for env, env_data in self.export_data["envConfig"].items():
            create_dir(f"{export_dir}/envConfig/{env}")
            for resource, metadata in env_data.items():
                create_dir(f"{export_dir}/envConfig/{env}/{resource}")
                for res_name, res_metadata in metadata.items():
                    write_json(
                        f"{export_dir}/envConfig/{env}/{resource}/{res_name}.json", res_metadata)
                    
    def read_export_state(self, folder_path):
        folder_data = {}
        
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                if folder_data.get(item):
                    folder_data[item].append(self.read_export_state(item_path))
                else:
                    folder_data[item] = self.read_export_state(item_path)
            else:
                with open(item_path, "r") as json_file:
                    json_content = json.load(json_file)
                    folder_data[item[:-5]]=json_content

        return folder_data


    def get_dependencies_data(self, dependencies):

        dependencies_data = {}

        for dependency in dependencies:
            dependencies_data[dependency] = {}
            if dependency == 'references':
                envs = self.opdk.list_environments()
                for env in envs:
                    dependencies_data[dependency][env] = {}
                    references = self.opdk.list_env_objects(env, dependency)
                    for reference in references:
                        dependencies_data[dependency][env][reference] = self.opdk.get_env_object(
                            env, dependency, reference)
            else:
                org_objects = self.opdk.list_org_objects(dependency)
                for each_org_object in org_objects:
                    dependencies_data[dependency][each_org_object] = self.opdk.get_org_object(
                        dependency, each_org_object)

        return dependencies_data
