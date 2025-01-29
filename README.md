# Apigee Migration Assessment Tool

[![Build Status](https://github.com/apigee/apigee-migration-assessment-tool/actions/workflows/tests.yml/badge.svg)](https://github.com/apigee/apigee-migration-assessment-tool/actions/workflows/tests.yml)

This tool helps you plan your migration from Apigee Edge / Apigee X / Apigee Hybrid to Apigee X/Hybrid by analyzing your source environment and generating a report.

Below table shows the supported assessment scenarios.

## Assessment Scenarios

| Source Apigee  | Target Apigee |
| -------- | ------- |
| Apigee Edge SAAS  | Apigee X |
| Apigee Edge SAAS  | Apigee Hybrid |
| Apigee Edge OPDK  | Apigee X |
| Apigee Edge OPDK  | Apigee Hybrid |
| Apigee Hybrid  | Apigee X |
| Apigee X  | Apigee Hybrid |

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

    Create an `input.properties` file in the **same directory** as the Python scripts.
    Please find sample inputs in the `sample/inputs` folder
    * [sample opdk input](sample/inputs/opdk.input.properties)
    * [sample saas input](sample/inputs/saas.input.properties)
    * [sample x/hybrid input](sample/inputs/x.input.properties)

    Refer the below table to set the required inputs in the `input` section of `input.properties` file.

    | Section  | Input   | Description |
    | -------- | ------- | ------- |
    | `input`  | `SOURCE_URL`    | Apigee OPDK/Edge/X/Hybrid Management URL |
    | `input`  | `SOURCE_ORG`     | Apigee OPDK/Edge Organization|
    | `input`  | `SOURCE_AUTH_TYPE`    | Apigee OPDK/Edge auth type , `basic` OR `oauth`|
    | `input`  | `SOURCE_UI_URL`    | Apigee OPDK/Edge UI URL, use default|
    | `input`  | `SOURCE_APIGEE_VERSION`     | APIGEE Flavor `OPDK` OR `SAAS` OR `X` OR `HYBRID`|
    | `input`  | `GCP_PROJECT_ID`    | GCP Project ID running Apigee X/Hybrd. Trial orgs are supported|
    | `input`  | `API_URL`    | Apigee API url, use default |
    | `input`  | `GCP_ENV_TYPE`     | Apigee X/Hybrid desired environment type |
    | `input`  | `TARGET_DIR`    | Name of directory to export apigee objects |
    | `input`  | `SSL_VERIFICATION`    | Set to `false` , to ignore SSL verification else set it to `true`|

2. **Generate Apigee Edge SAAS/OPDK/X/Hybrud Auth Tokens:**

    * Basic Auth:
    ```bash
    export SOURCE_AUTH_TOKEN=`echo -n '<username>:<password>' | base64`
    ```
    *  OAuth2/SAML:
    
        - For Apigee Edge [Apigee Edge Management API documentation](https://docs.apigee.com/api-platform/system-administration/management-api-overview) for generating OAuth2 tokens.
        ```bash
        export SSO_LOGIN_URL=https://login.apigee.com  # Example
        export SOURCE_AUTH_TOKEN=$(get_token -u <user>:<password> -m xxxx) # Example using a helper script
        ```
        - For Apigee X/Hybrid as source
        ```bash
        export SOURCE_AUTH_TOKEN=$(gcloud auth print-access-token)
        ```

3. **Generate Apigee X/Hybrid Auth Tokens:**
    ```bash
    export APIGEE_ACCESS_TOKEN=$(gcloud auth print-access-token)
    ```
4. **Run the Tool:**

    * **Local Run:**
        ```bash
        python3 main.py --resources <resources>
        ```

    * **Docker Run:**
        ```bash
        mkdir output
        sudo chmod 777 output
        export DOCKER_IMAGE="<image_name>:<tag>"
        docker run --rm   -v "$(pwd)/output:/app/target" \
            -v "$(pwd)/input.properties:/app/input.properties" \
            -e SOURCE_AUTH_TOKEN=$SOURCE_AUTH_TOKEN \
            -e APIGEE_ACCESS_TOKEN=$APIGEE_ACCESS_TOKEN \
            $DOCKER_IMAGE --resources all
        ```

        Eg.
        ```bash
        mkdir output
        sudo chmod 777 output
        export DOCKER_IMAGE="ghcr.io/apigee/apigee-migration-assessment-tool/apigee-migration-assessment-tool:latest"
        docker run --rm   -v "$(pwd)/output:/app/target" \
            -v "$(pwd)/input.properties:/app/input.properties" \
            -e SOURCE_AUTH_TOKEN=$SOURCE_AUTH_TOKEN \
            -e APIGEE_ACCESS_TOKEN=$APIGEE_ACCESS_TOKEN \
            $DOCKER_IMAGE --resources all
        ```

## Accessing the Report and Visualization

1. **Assessment Report:**
    `qualification_report.xlsx` in the TARGET_DIR (specified in input.properties).

    Please find [sample assessment](sample/outputs/sample_qualification_report.xlsx) in the [sample/outputs](sample/outputs) folder

2. **Visualization:**
    `visualization.html` in the `TARGET_DIR`. Open this file in a web browser.
    Refer the sample visualization

    ![alt text](assets/visualization.png) .


## Contributing
We welcome contributions from the community. If you would like to contribute to this project, please see our [Contribution Guidelines](./CONTRIBUTING.md).

## License

All solutions within this repository are provided under the
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
Please see the [LICENSE](./LICENSE) file for more detailed terms and conditions.

## Disclaimer

This repository and its contents are not an official Google product.
