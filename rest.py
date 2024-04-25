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

import json
import requests
from base_logger import logger, EXEC_INFO

UNKNOWN_ERROR = 'internal.unknown'


class ApigeeError(Exception):
    def __init__(self, status_code, error_code, message):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message

    def __str__(self):
        return '{}: {}'.format(self.status_code, self.message)


class RestClient(object):

    """Provides simple methods for handling all RESTful api endpoints. """

    def __init__(self, auth_type, token):
        self._ALLOWED_AUTH_TYPES = ['basic', 'oauth']
        if auth_type not in self._ALLOWED_AUTH_TYPES:
            raise ValueError(
                f'Unknown Auth type , Allowed types are {" ,".join(self._ALLOWED_AUTH_TYPES)}')
        self.auth_type = auth_type

        self.base_headers = {
            'Authorization': f'Basic {token}' if auth_type == 'basic' else f'Bearer {token}'
        }

    def get(self, url, params=None):
        headers = self.base_headers.copy()
        response = requests.get(url, params=params, headers=headers)
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def file_get(self, url, params=None):
        headers = self.base_headers.copy()
        response = requests.get(
            url, params=params, headers=headers, stream=True)
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def post(self, url, data=None):
        headers = self.base_headers.copy()
        response = requests.post(
            url, data=json.dumps(data or {}), headers=headers)
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def file_post(self, url, params=None, data=None, files=None):
        headers = self.base_headers.copy()
        headers['Content-Type'] = 'application/octet-stream'
        response = requests.post(
            url, data=data, files=files, headers=headers, params=params)
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def patch(self, url, data=None):
        headers = self.base_headers.copy()
        response = requests.patch(
            url, data=json.dumps(data or {}), headers=headers)
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def put(self, url, data=None):
        headers = self.base_headers.copy()
        response = requests.put(
            url, data=json.dumps(data or {}), headers=headers)
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def delete(self, url, params=None):
        headers = self.base_headers.copy()
        response = requests.delete(url, headers=headers, params=params or {})
        logger.debug(f"Response: {response.content}")
        return self._process_response(response)

    def _process_response(self, response):
        return self._parse(response).content()

    def _parse(self, response):
        if not response.text:
            return EmptyResponse(response.status_code)
        if response.headers['Content-Type'] == 'application/octet-stream':
            return RawResponse(response)
        try:
            return JsonResponse(response)
        except ValueError:
            logger.error('Unable to parse response as JSON',
                         exc_info=EXEC_INFO)
            return PlainResponse(response)


class Response(object):
    def __init__(self, status_code, content):
        self._status_code = status_code
        self._content = content

    def content(self):
        if self._is_error():
            raise ApigeeError(status_code=self._status_code,
                              error_code=self._error_code(),
                              message=self._error_message())
        else:
            return self._content

    def _is_error(self):
        return self._status_code is None  # or self._status_code >= 400

    # Adding these methods to force implementation in subclasses because they are references in this parent class
    def _error_code(self):
        raise NotImplementedError

    def _error_message(self):
        raise NotImplementedError


class JsonResponse(Response):
    def __init__(self, response):
        content = json.loads(response.text)
        super(JsonResponse, self).__init__(response.status_code, content)

    def _error_code(self):
        if 'errorCode' in self._content:
            return self._content.get('errorCode')
        elif 'error' in self._content:
            return self._content.get('error')
        else:
            return UNKNOWN_ERROR

    def _error_message(self):
        message = self._content.get('message', '')
        if message is not None and message != '':
            return message
        return self._content.get('error', '')


class PlainResponse(Response):
    def __init__(self, response):
        super(PlainResponse, self).__init__(
            response.status_code, response.text)

    def _error_code(self):
        return UNKNOWN_ERROR

    def _error_message(self):
        return self._content


class EmptyResponse(Response):
    def __init__(self, status_code):
        super(EmptyResponse, self).__init__(status_code, '')

    def _error_code(self):
        return UNKNOWN_ERROR

    def _error_message(self):
        return ''


class RawResponse(Response):
    def __init__(self, response):
        content = response.content
        super(RawResponse, self).__init__(response.status_code, content)

    def _error_code(self):
        return UNKNOWN_ERROR

    def _error_message(self):
        return self._content
