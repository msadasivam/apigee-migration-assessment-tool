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
from rest import RestClient, ApigeeError
from requests.utils import quote as urlencode
from base_logger import logger, EXEC_INFO


class ApigeeNewGen():
    def __init__(self, project_id, token, env_type):
        self.baseurl = 'https://apigee.googleapis.com/v1'
        self.project_id = project_id
        self.token = token
        self.env_type = env_type or 'ENVIRONMENT_TYPE_UNSPECIFIED'
        self.client = RestClient('oauth', token)

    def get_env_object(self, env, env_object, env_object_name):
        if env_object == 'resourcefiles':
            url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object}/{env_object_name['type']}/{env_object_name['name']}"
            env_object = self.client.get(url)
        else:
            url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object}/{env_object_name}"
            env_object = self.client.get(url)
        return env_object

    def create_api(self, api_type, api_name, proxy_bundle_path, action):
        url = f"{self.baseurl}/organizations/{self.project_id}/{api_type}?name={api_name}"
        params = {
            'action': action,
            'validate': True
        }
        files = [
            ('data', (api_name, open(proxy_bundle_path, 'rb'), 'application/zip'))
        ]
        api_object = self.client.file_post(url, params, None, files)
        return api_object
