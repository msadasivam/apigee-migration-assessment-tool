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

"""Main module for the Apigee Migration Assessment Tool.

This module orchestrates the assessment process:
1. Parses input configurations.
2. Performs pre-validation checks.
3. Exports Apigee artifacts.
4. Validates the exported artifacts against Apigee X requirements.
5. Visualizes the assessment results.
6. Retrieves Apigee topology information (for on-prem).
7. Generates a qualification report.
"""

import os
import argparse
from core_wrappers import (
    pre_validation_checks, export_artifacts,
    validate_artifacts, visualize_artifacts, get_topology,
    qualification_report)
from utils import (
    write_json,
    parse_json,
    parse_config
)
from base_logger import logger


def main():
    """Main function to execute the assessment workflow.

    Parses command-line arguments for resource selection,
    then executes the steps of the Apigee migration assessment:
    export, validation, visualization, topology retrieval (on-prem),
    and qualification report generation.  Handles caching of results
    between steps to avoid redundant operations.
    """
    # Parse Input
    parser = argparse.ArgumentParser(
        description='details',
        usage='use "%(prog)s --help" for more information',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--resources',
                        type=str,
                        dest='resources',
                        # help='Resources to be exported',
                        help="""
        resources can be one of or comma seperated list of

        * targetservers
        * keyvaluemaps
        * references
        * resourcefiles
        * keystores
        * flowhooks
        * developers
        * apiproducts
        * apis
        * apps

        For Apigee Environment level objects choose
        -> targetservers,keyvaluemaps,references,
            resourcefiles,keystores,flowhooks

        For Apigee Organization level objects choose
        -> org_keyvaluemaps,developers,apiproducts,
            apis,apps,sharedflows

        Example1: --resources targetservers,keyvaluemaps
        Example2: --resources keystores,apps
                        """)
    parser.add_argument('--skip-validation',
                        action='store_true',
                        dest='skip_validation',
                        help='''Skip validation steps that require an API call to a target Apigee environment.
    This allows for partial validation when a target is unavailable.
    Specifically, it skips API/SharedFlow bundle validation and FlowHook validation.''')

    args = parser.parse_args()
    resources_list = args.resources.split(',') if args.resources else []
    skip_validation = args.skip_validation

    # Pre validation checks
    cfg = parse_config('input.properties')
    backend_cfg = parse_config('backend.properties')
    if not pre_validation_checks(cfg, skip_validation):
        logger.error("Pre validation checks failed. Please, check...")
        return

    topology_mapping = {}
    target_dir = cfg.get('inputs', 'TARGET_DIR')
    export_dir = backend_cfg.get('export', 'EXPORT_DIR')
    export_file = backend_cfg.get('export', 'EXPORT_FILE')
    export_data_file = f"{target_dir}/{export_dir}/{export_file}"
    export_data = parse_json(export_data_file)

    report_data_file = f"{target_dir}/{export_dir}/report.json"
    report = parse_json(report_data_file)

    if not export_data.get('export', False):
        export_data['export'] = False
        topology_mapping = {}

        # Export Artifacts from Apigee OPDK/Edge (4G)
        if resources_list == []:
            logger.error(
                '''Please specify --resources argument.
                Use -h with the script for help''')
            return

        export_data = export_artifacts(cfg, resources_list)
        export_data['export'] = True
        write_json(export_data_file, export_data)

    if (not report.get('report', False) or
            not export_data.get('validation_report', False)):
        report = validate_artifacts(cfg, resources_list, export_data, skip_validation)
        report['report'] = True
        export_data['validation_report'] = report
        write_json(export_data_file, export_data)
        write_json(report_data_file, report)
    # Visualize artifacts
    if not os.environ.get("IGNORE_VIZ") == "true":
        visualize_artifacts(cfg, export_data, report)

    # get Apigee OPDK/Edge (4G) topology mapping
    if not os.environ.get("IGNORE_OPDK_TOPOLOGY") == "true":
        source_apigee_version = cfg.get('inputs', 'SOURCE_APIGEE_VERSION')
        if source_apigee_version == 'OPDK':
            topology_mapping = get_topology(cfg)

    # Qualification report
    qualification_report(cfg, backend_cfg, export_data, topology_mapping)


if __name__ == '__main__':
    main()
