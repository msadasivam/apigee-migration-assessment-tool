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

from assessment_mapping.targetservers import targetservers_mapping
from assessment_mapping.resourcefiles import resourcefiles_mapping
import copy
from nextgen import ApigeeNewGen
from utils import *

class ApigeeValidator():

    def __init__(self,project_id,token, env_type):
        self.project_id=project_id
        self.xorhybrid = ApigeeNewGen(project_id,token, env_type)
    
    def validate_env_targetservers(self, targetServers):
        validation_targetservers = []
        for targetServer in targetServers.keys():
            obj = copy.copy(targetServers[targetServer])
            obj['importable'], obj['reason'] = self.validate_env_targetserver_resource(targetServers[targetServer])
            validation_targetservers.append(obj)

        return validation_targetservers

    def validate_env_targetserver_resource(self, targetservers):
        errors = []
        for key in targetservers_mapping.keys():
            if targetservers[key] in targetservers_mapping[key]['invalid_values'].keys():
                errors.append({
                    'key': key,
                    'error_msg': targetservers_mapping[key]['invalid_values'][targetservers[key]],
                })

        if len(errors) == 0:
            return True, [] 
        else:
            return False, errors

    def validate_env_resourcefiles(self, resourcefiles):
        validation_rfiles = []
        for resourcefile in resourcefiles.keys():
            obj = copy.copy(resourcefiles[resourcefile])
            obj['importable'], obj['reason'] = self.validate_env_resourcefile_resource(resourcefiles[resourcefile])
            validation_rfiles.append(obj)

        return validation_rfiles

    def validate_env_resourcefile_resource(self, metadata):
        errors = []
        for key in resourcefiles_mapping.keys():
            if metadata[key] in resourcefiles_mapping[key]['invalid_values'].keys():
                errors.append({
                    'key': key,
                    'error_msg': resourcefiles_mapping[key]['invalid_values'][metadata[key]],
                })

        if len(errors) == 0:
            return True, [] 
        else:
            return False, errors
    
    def validate_proxy_bundles(self,export_dir):
        validation = {'apis':[],'sharedflows':[]}
        for each_api_type in ['apis','sharedflows']:
            for proxy_bundle in list_dir(export_dir):
                each_validation = self.validate_proxy(export_dir,each_api_type,proxy_bundle)
                validation[each_api_type].append(each_validation)
        return validation

    @retry()
    def validate_proxy(self,export_dir,each_api_type,proxy_bundle):
        api_name=proxy_bundle.split(".zip")[0]
        validation_response = self.xorhybrid.create_api(
                                each_api_type,
                                api_name,
                                f"{export_dir}/{proxy_bundle}",
                                'validate'
                            )
        obj = copy.copy(validation_response)
        if 'error' in validation_response:
            obj['name']=api_name
            obj['importable'], obj['reason'] = False,validation_response['error'].get('details','ERROR')
        else:
            obj['importable'], obj['reason'] = True,[]
        return obj
    
    def validate_env_flowhooks(self, env, flowhooks):
        
        validation_flowhooks = []
        for flowhook in flowhooks.keys():

            obj = copy.copy(flowhooks[flowhook])
            obj['name'] = flowhook # Name is required for Visualization tool
            obj['importable'], obj['reason'] = self.validate_env_flowhooks_resource(env, flowhooks[flowhook])
            validation_flowhooks.append(obj)

        return validation_flowhooks

    def validate_env_flowhooks_resource(self, env, flowhook):

        errors = []
        if "sharedFlow" in flowhook:
            
            envSharedFlowDeployment = self.xorhybrid.get_env_object(env, "sharedflows", flowhook["sharedFlow"]+"/deployments")
            if "deployments" in envSharedFlowDeployment and len(envSharedFlowDeployment["deployments"]) == 0:
                errors.append({
                    'key': "sharedFlow",
                    'error_msg': f"Flowhook sharedflow - {flowhook['sharedFlow']} is not present in APIGEE X environment {env}",
                })

        if len(errors) == 0:
            return True, [] 
        else:
            return False, errors
