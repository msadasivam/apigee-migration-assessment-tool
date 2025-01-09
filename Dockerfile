
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

FROM python:3.11-alpine
# Create a directory to hold the persistent data

RUN addgroup -S apigee && \
    adduser -S apigee -G apigee && \
    mkdir -p /app && \
    chown apigee:apigee /app && \
    apk add --no-cache graphviz=12.2.0-r0

USER apigee

WORKDIR /app

# Copy the requirements file
COPY requirements.txt requirements.txt

RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

HEALTHCHECK \
    CMD python -c 'print()'

# Set the entrypoint to execute the Python script
ENTRYPOINT ["python3", "main.py"]
