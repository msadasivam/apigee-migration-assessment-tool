#!/usr/bin/python

# Copyright 2025 Google LLC
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

"""Interacts with Apigee X or hybrid using the Management API.

This module provides a client for interacting with Apigee X or hybrid.
It offers methods for creating and validating API proxies and sharedflows.
"""

from rest import RestClient


class ApigeeNewGen():
    """A client for interacting with Apigee X or hybrid.

    Provides methods to interact with Apigee X or hybrid environments,
    including creating and validating API proxies and shared flows.
    """
    def __init__(self, project_id, token, env_type):
        """Initializes the ApigeeNewGen client.

        Args:
            project_id (str): The Google Cloud project ID.
            token (str): The OAuth2 access token.
            env_type (str): The environment type ('hybrid' or 'x').
                            Defaults to 'ENVIRONMENT_TYPE_UNSPECIFIED'.
        """
        self.baseurl = 'https://apigee.googleapis.com/v1'
        self.project_id = project_id
        self.token = token
        self.env_type = env_type or 'ENVIRONMENT_TYPE_UNSPECIFIED'
        self.client = RestClient('oauth', token)

    def get_org(self):
        """Retrieves details of the Apigee organization.

        Returns:
            dict: A dictionary containing the organization details.
        """
        url = f"{self.baseurl}/organizations/{self.project_id}"
        org = self.client.get(url)
        return org

    def get_env_object(self, env, env_object, env_object_name):
        """Retrieves an environment-level object.

        Args:
            env (str): The environment name.
            env_object (str): The object type (e.g., 'resourcefiles').
            env_object_name (str or dict): The object name or identifier.

        Returns:
            dict: The environment object details.
        """
        if env_object == 'resourcefiles':
            url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object}/{env_object_name['type']}/{env_object_name['name']}"   # noqa pylint: disable=C0301
            env_object = self.client.get(url)
        else:
            url = f"{self.baseurl}/organizations/{self.project_id}/environments/{env}/{env_object}/{env_object_name}"    # noqa pylint: disable=C0301
            env_object = self.client.get(url)
        return env_object

    def create_api(self, api_type, api_name, proxy_bundle_path, action):
        """Creates or validates an API proxy or sharedflow.

        Args:
            api_type (str): The type ('apis' or 'sharedflows').
            api_name (str): The name of the proxy/flow.
            proxy_bundle_path (str): Path to the proxy/flow bundle.
            action (str): The action ('create' or 'validate').

        Returns:
            dict: The API creation/validation response.

        """
        url = f"{self.baseurl}/organizations/{self.project_id}/{api_type}?name={api_name}"   # noqa pylint: disable=C0301
        params = {
            'action': action,
            'validate': True
        }
        files = [
            ('data', (api_name, open(proxy_bundle_path, 'rb'), 'application/zip'))   # noqa pylint: disable=C0301,R1732
        ]
        api_object = self.client.file_post(url, params, None, files)
        return api_object
