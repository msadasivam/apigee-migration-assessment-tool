# Apigee Migration Assessment Tool

[![Build Status](https://github.com/apigee/apigee-migration-assessment-tool/actions/workflows/tests.yml/badge.svg)](https://github.com/apigee/apigee-migration-assessment-tool/actions/workflows/tests.yml)

This tool helps you plan your migration from Apigee Edge (OPDK or SaaS) to Apigee X/Hybrid by analyzing your source environment and generating a report.

## Prerequisites

You can run this tool locally or using Docker.

* **Local:** Requires installing Python libraries and dependencies.
* **Docker:**  You can build the image yourself.

### Local Setup

1. **Install Graphviz:** Follow the instructions at https://graphviz.org/download/

2. **Install Python venv:**

   ```bash
   python3 -m pip install virtualenv==20.24.4
   ```
3. **Create and activate a virtual environment:**
   ```bash
    python3 -m venv dev
    source dev/bin/activate
   ```
4. **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Docker Setup
1.  **Use a pre-built Docker image:**
    ```bash
    docker pull ghcr.io/apigee/apigee-migration-assessment-tool/apigee-migration-assessment-tool:latest
    ```
    **OR**

    **Build the Docker image:**
    ```bash
    docker build -t <image_name>:<tag> .
    docker push <image_name>:<tag>
    ```

2. **Run the Docker image:**
    ```bash
    docker run <image_name>:<tag>
    ```

## Apigee Permissions
* **Apigee Edge SAAS/OPDK**

   The tool requires permissions to export all objects from Apigee Egde. Hence assign the following permission to relevant user.
   * `Read-only Organization Administrator`

   Refer: [edge-built-roles](https://docs.apigee.com/api-platform/system-administration/edge-built-roles)

* **Apigee X/Hybrid**

   The tool requires readonly permissions to org, env & env objects. The tool also requires permissions to validate apis. Hence assign the below permissions to relevant user or service account.
   * A built-in role `roles/apigee.readOnlyAdmin`
   * A custom role with `apigee.proxies.create` permission
        ```bash
        gcloud iam roles create ApigeeAPIValidator --project=<PROJECT_ID> \
        --title="Apigee API Validator" --description="Apigee API Import validator" \
        --permissions="apigee.proxies.create" --stage=Alpha
        ```
    Refer: [apigee-roles](https://cloud.google.com/iam/docs/understanding-roles#apigee-roles)

## Tool Usage
1. **Complete Assessment**

    To assess all Apigee objects:
    ```bash
    python3 main.py --resources all
    ```

2. **Selective Assessment**

    To assess specific Apigee objects, use the --resources flag followed by a comma-separated list:
    ```bash
    python3 main.py --resources <resource1>,<resource2>,...
    ```
    Available resources:
    * Environment Level: targetservers, keyvaluemaps, references, resourcefiles, keystores, flowhooks
    * Organization Level: org_keyvaluemaps, developers, apiproducts, apis, apps, sharedflows

    Examples

    ```bash
    python3 main.py --resources targetservers,keyvaluemaps
    python3 main.py --resources keystores,apps
    ```
## Running the Tool
1. **Prepare input.properties**

    Create an input.properties file in the same directory as the Python scripts. See the example below. Replace the placeholder values with your actual Apigee configuration details.
    ```
    [inputs]      
    SOURCE_URL=https://xxx/v1                # Apigee OPDK/Edge Management URL 
    SOURCE_ORG=xxx                           # Apigee OPDK/Edge Organization
    SOURCE_AUTH_TYPE=basic | oauth           # Apigee OPDK/Edge auth type , basic or oauth
    SOURCE_UI_URL=https://xxx                # Apigee OPDK/Edge UI URL
    SOURCE_APIGEE_VERSION=xxxx               # APIGEE Flavor OPDK/SAAS/X/HYBRID
    GCP_PROJECT_ID=xx-xx-xx                  # Apigee X/Hybrd Organiziation ID
    API_URL=https://xxx/docs                 # Apigee API url
    GCP_ENV_TYPE=BASE | INTERMEDIATE | COMPREHENSIVE    # Apigee X/Hybrid desired environment type
    TARGET_DIR=target                        # Name of directory to export apigee objects 
    SSL_VERIFICATION=true                    # Set to false , to ignore SSL verification

    [export]
    EXPORT_DIR=export
    EXPORT_FILE=export_data.json

    [topology]
    TOPOLOGY_DIR=topology
    NW_TOPOLOGY_MAPPING=pod_component_mapping.json
    DATA_CENTER_MAPPING=data_center_mapping.json

    [report]
    QUALIFICATION_REPORT=qualification_report.xlsx

    [visualize]
    VISUALIZATION_GRAPH_FILE=visualization.html

    [validate]
    CSV_REPORT=report.csv
    ```
2. **Generate Apigee Edge SAAS/OPDK Auth Tokens:**

    * Basic Auth:
    ```bash
    export SOURCE_AUTH_TOKEN=`echo -n '<username>:<password>' | base64`
    ```
    *  OAuth2/SAML:
    
    Refer to the [Apigee documentation](https://docs.apigee.com/api-platform/system-administration/management-api-overview) for generating OAuth2 tokens.
    ```bash
    export SSO_LOGIN_URL=https://login.apigee.com  # Example
    export SOURCE_AUTH_TOKEN=$(get_token -u <user>:<password> -m xxxx) # Example using a helper script
    ```

3. **Generate Apigee X/Hybrid Auth Tokens:**
    ```bash
    export APIGEE_ACCESS_TOKEN=$(gcloud auth print-access-token)
    ```
4. **Run the Tool:**

    * Local Run:
    ```bash
    python3 main.py --resources <resources>
    ```

    * Docker Run:
    ```bash
    export DOCKER_IMAGE="<image_name>:<tag>"

    docker run --rm   -v "$(pwd)/output:/app/target" \
        -v "$(pwd)/input.properties:/app/input.properties" \
        -e SOURCE_AUTH_TOKEN=$SOURCE_AUTH_TOKEN \
        -e APIGEE_ACCESS_TOKEN=$APIGEE_ACCESS_TOKEN \
        $DOCKER_IMAGE --resources all
    ```

## Accessing the Report and Visualization

1. **Assessment Report:**
    qualification_report.xlsx in the TARGET_DIR (specified in input.properties).
2. **Visualization:**
    visualization.html in the TARGET_DIR. Open this file in a web browser. 
    See the ![alt text](assets/visualization.png) for a sample visualization.


## Contributing
We welcome contributions from the community. If you would like to contribute to this project, please see our [Contribution Guidelines](./CONTRIBUTING.md).

## License

All solutions within this repository are provided under the
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
Please see the [LICENSE](./LICENSE) file for more detailed terms and conditions.

## Disclaimer

This repository and its contents are not an official Google product.
