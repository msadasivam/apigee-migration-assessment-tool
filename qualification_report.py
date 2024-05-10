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

import xlsxwriter
from qualification_report_mapping.header_mapping import (
    topology_installation_mapping, proxies_per_env_mapping,
    northbound_mtls_mapping, company_and_developers_mapping,
    anti_patterns_mapping, cache_without_expiry_mapping,
    apps_without_api_products_mapping, json_path_enabled_mapping,
    cname_anomaly_mapping, unsupported_polices_mapping,
    api_limits_mapping,
    org_limits_mapping,
    env_limits_mapping,
    api_with_multiple_basepath_mapping,
    sharding_output,
    aliases_with_private_keys,
    sharded_proxies,
    org_resourcefiles,
)
from qualification_report_mapping.report_summary import report_summary
from base_logger import logger


class QualificationReport():

    def __init__(self, workbookname, export_data, topology_mapping, cfg, backend_cfg, orgName):
        self.workbook = xlsxwriter.Workbook(workbookname)
        self.export_data = export_data
        self.topology_mapping = topology_mapping
        self.orgName = orgName
        self.cfg = cfg
        self.backend_cfg = backend_cfg
        # Heading formats
        self.heading_format = self.workbook.add_format(
            {'bold': True, 'bg_color': 'lightblue', 'font_color': 'white'})

        # Format to represent resource migration status
        self.danger_format = self.workbook.add_format({'bg_color': '#f5cbcc'})
        self.yellow_format = self.workbook.add_format({'bg_color': 'yellow'})

        # Information blue box formats
        self.info_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'font_size': 12, 'valign': 'top'})
        self.info_bold_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'bold': True, 'font_size': 18})
        self.info_italic_underline_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'italic': True, 'underline': True, 'font_size': 14})
        self.info_bold_underline_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'bold': True, 'underline': True, 'font_size': 14})
        self.ref_link_heading_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'bold': True, 'underline': True, 'font_size': 14})
        self.ref_link_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'bold': False, 'underline': True, 'font_size': 12, 'font_color': 'blue'})

        # Qualification Report Summary
        self.summary_main_header_format = self.workbook.add_format(
            {'bg_color': '#4285f4', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'bold': True, 'font_size': 24, 'valign': 'center'})
        self.summary_block_header_format = self.workbook.add_format(
            {'bg_color': '#000000', 'font_color': 'white', 'border': 1, 'text_wrap': True, 'font_size': 18, 'valign': 'center'})
        self.summary_link_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'underline': True, 'font_size': 16, 'font_color': 'blue'})
        self.summary_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'font_size': 16, 'font_color': 'black'})
        self.summary_note_blue_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'font_size': 13, 'font_color': 'blue', 'valign': 'center', "align": "center"})
        self.summary_note_green_format = self.workbook.add_format(
            {'border': 1, 'text_wrap': True, 'font_size': 13, 'font_color': 'green', 'valign': 'center', "align": "center"})
        self.summary_cell_danger_format = self.workbook.add_format(
            {'bg_color': '#f5cbcc', 'valign': 'vcenter', "align": "center", 'border': 1, 'text_wrap': True, 'font_size': 16})
        self.summary_cell_green_format = self.workbook.add_format(
            {'bg_color': '#5fbd76', 'valign': 'vcenter', "align": "center", 'border': 1, 'text_wrap': True, 'font_size': 16})

    # Sheet column heading
    def qualification_report_heading(self, headers, sheet):
        # Headings
        col = 0
        alph = 65
        for val in headers:
            sheet.write(f'{chr(alph)}1', val, self.heading_format)
            sheet.set_column(col, col, len(val) + 1)
            col = col+1
            alph = alph+1

    # Get final information box text
    def get_final_info_text_and_format_arr(self, full_text):
        final_text = []
        for line in full_text.split('\n'):
            if line.startswith("<b>"):
                final_text.append(self.info_bold_format)
                final_text.append(line.split("<b>")[1]+'\n')
            elif line.startswith("<iu>"):
                final_text.append(self.info_italic_underline_format)
                final_text.append(line.split("<iu>")[1]+'\n')
            elif line.startswith("<bu>"):
                final_text.append(self.info_bold_underline_format)
                final_text.append(line.split("<bu>")[1]+'\n')
            else:
                final_text.append(self.info_format)
                final_text.append(line+'\n')

        final_text.append(self.info_format)

        return final_text

    def qualification_report_info_box(self, mapping_json, sheet):
        # Information box
        alph = 65 + len(mapping_json["headers"])

        if (type(mapping_json["info_block"]) is dict):
            sheet.set_column(len(mapping_json["headers"]), len(mapping_json["headers"])+int(mapping_json["info_block"]["col_merge"]), len(
                mapping_json["info_block"]["text"].split("\n")[int(mapping_json["info_block"]["text_line_no_for_col_count"])]) / int(mapping_json["info_block"]["col_merge"]))

            final_text = self.get_final_info_text_and_format_arr(
                mapping_json["info_block"]["text"])

            sheet.merge_range(
                f'{chr(alph)}{int(mapping_json["info_block"]["start_row"])}:{chr(alph+(int(mapping_json["info_block"]["col_merge"])-1))}{int(mapping_json["info_block"]["end_row"])}', "", self.info_format)
            sheet.write_rich_string(
                f'{chr(alph)}{int(mapping_json["info_block"]["start_row"])}', *final_text)

        elif (type(mapping_json["info_block"]) is list):
            for block in mapping_json["info_block"]:
                if "text_line_no_for_col_count" in block:
                    sheet.set_column(len(mapping_json["headers"]), len(mapping_json["headers"])+int(block["col_merge"]), len(
                        block["text"].split("\n")[int(block["text_line_no_for_col_count"])]) / int(block["col_merge"]))

                final_text = self.get_final_info_text_and_format_arr(
                    block["text"])

                sheet.merge_range(
                    f'{chr(alph)}{int(block["start_row"])}:{chr(alph+(int(block["col_merge"])-1))}{int(block["end_row"])}', "", self.info_format)
                sheet.write_rich_string(
                    f'{chr(alph)}{int(block["start_row"])}', *final_text)

        link_start_row = int(mapping_json["info_block"]["end_row"])+2 if type(mapping_json["info_block"]
                                                                              ) is dict else mapping_json["info_block"][len(mapping_json["info_block"])-1]["end_row"]+2

        if ("link" in mapping_json["info_block"] or "link" in mapping_json):

            link_arr = mapping_json["info_block"]["link"] if type(
                mapping_json["info_block"]) is dict else mapping_json["link"]

            sheet.write_string(f'{chr(alph)}{int(link_start_row)}',
                               f"Reference Link{'s:' if len(link_arr) > 1 else ':'}", self.ref_link_heading_format)
            link_start_row = link_start_row+1

            for link_item in link_arr:
                sheet.write_url(f'{chr(alph)}{link_start_row}',
                                link_item["link"], self.ref_link_format, string=link_item["link_text"])
                link_start_row = link_start_row+1

    def report_proxies_per_env(self):

        # Worksheet 1 - [Proxies Per Env]
        logger.info(
            '------------------- Proxies Per Env -----------------------')
        proxiesPerEnvSheet = self.workbook.add_worksheet(
            name='Proxies Per Env')

        # Headings
        self.qualification_report_heading(
            proxies_per_env_mapping["headers"], proxiesPerEnvSheet)

        envConfig = self.export_data.get('envConfig')
        row = 1

        allowed_no_of_proxies_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_PROXIES_PER_ENV_LIMITS')
        allowed_no_of_shared_flows_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_SHARED_FLOWS_PER_ENV_LIMITS')
        allowed_no_of_proxies_and_shared_flows_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_PROXIES_AND_SHARED_FLOWS_PER_ENV_LIMITS')

        for key, value in envConfig.items():
            # Org name
            col = 0
            proxiesPerEnvSheet.write(row, col, self.orgName)
            # Env name
            col += 1
            proxiesPerEnvSheet.write(row, col, key)
            # No of Proxies
            col += 1
            noOfProxies = len(value['apis'])
            if (noOfProxies > int(allowed_no_of_proxies_per_env)):
                proxiesPerEnvSheet.write(
                    row, col, noOfProxies, self.danger_format)
            else:
                proxiesPerEnvSheet.write(row, col, noOfProxies)
            # No of Sharedflows
            col += 1
            noOfSharedFlows = len(value['sharedflows'])
            if (noOfSharedFlows > int(allowed_no_of_shared_flows_per_env)):
                proxiesPerEnvSheet.write(
                    row, col, noOfSharedFlows, self.danger_format)
            else:
                proxiesPerEnvSheet.write(row, col, noOfSharedFlows)
            # Total no of Proxies & Sharedflows
            col += 1
            totalOfProxiesAndSharedFlows = (noOfProxies + noOfSharedFlows)
            if (totalOfProxiesAndSharedFlows > int(allowed_no_of_proxies_and_shared_flows_per_env)):
                proxiesPerEnvSheet.write(
                    row, col, totalOfProxiesAndSharedFlows, self.danger_format)
            else:
                proxiesPerEnvSheet.write(
                    row, col, totalOfProxiesAndSharedFlows)
            row += 1

        proxiesPerEnvSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            proxies_per_env_mapping, proxiesPerEnvSheet)

    def report_north_bound_mtls(self):

        # Worksheet 3 - [Northbound mTLS]
        logger.info(
            '------------------- Northbound mTLS -----------------------')
        northBoundMTLSSheet = self.workbook.add_worksheet(
            name='Northbound mTLS')

        # Headings
        self.qualification_report_heading(
            northbound_mtls_mapping["headers"], northBoundMTLSSheet)

        envConfig = self.export_data.get('envConfig')
        row = 1

        for env, value in envConfig.items():
            vhosts = value['vhosts']
            for vhost, vhost_content in vhosts.items():
                # org name
                col = 0
                northBoundMTLSSheet.write(row, col, self.orgName)
                # Env name
                col += 1
                northBoundMTLSSheet.write(row, col, env)
                col += 1
                northBoundMTLSSheet.write(row, col, vhost)

                if vhost_content.get('sSLInfo'):
                    sslinfo = vhost_content['sSLInfo']
                    col += 1
                    northBoundMTLSSheet.write(
                        row, col, sslinfo['enabled'], self.danger_format)
                    col += 1
                    northBoundMTLSSheet.write(
                        row, col, sslinfo['clientAuthEnabled'], self.danger_format)
                    col += 1
                    if sslinfo.get('keyStore'):
                        northBoundMTLSSheet.write(
                            row, col, sslinfo['keyStore'], self.danger_format)
                    elif vhost_content.get("useBuiltInFreeTrialCert") == True:
                        northBoundMTLSSheet.write(
                            row, col, "Free Trial Cert Used", self.danger_format)

                else:
                    col += 1
                    northBoundMTLSSheet.write(row, col, 'False')
                row += 1

        northBoundMTLSSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            northbound_mtls_mapping, northBoundMTLSSheet)

    def report_company_and_developer(self):

        # Worksheet 4 - [Company And Developers]
        logger.info(
            '------------------- Company And Developers -----------------------')
        companiesAndDevelopers = self.workbook.add_worksheet(
            name='Company And Developers')

        # Headings
        self.qualification_report_heading(
            company_and_developers_mapping["headers"], companiesAndDevelopers)

        orgConfig = self.export_data.get('orgConfig')
        companies = orgConfig['companies']
        row = 1

        # Org name
        for company in companies:
            col = 0
            companiesAndDevelopers.write(row, col, self.orgName)
            col += 1
            companiesAndDevelopers.write(row, col, company)
            row += 1

        companiesAndDevelopers.autofit()
        # Info block
        self.qualification_report_info_box(
            company_and_developers_mapping, companiesAndDevelopers)

    def report_anti_patterns(self):

        # Worksheet 5 - [Anti Patterns]
        logger.info('------------------- Anti Patterns -----------------------')
        antiPatternsSheet = self.workbook.add_worksheet(name='Anti Patterns')

        # Headings
        self.qualification_report_heading(
            anti_patterns_mapping["headers"], antiPatternsSheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            AntiPatternQuota = values['qualification']['AntiPatternQuota']
            for policy, value in AntiPatternQuota.items():
                col = 0
                antiPatternsSheet.write(row, col, self.orgName)
                col += 1
                antiPatternsSheet.write(row, col, proxy)
                col += 1
                antiPatternsSheet.write(row, col, policy)
                col += 1
                antiPatternsSheet.write(row, col, value['distributed'])
                col += 1
                antiPatternsSheet.write(row, col, value['Synchronous'])

                row += 1

        antiPatternsSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            anti_patterns_mapping, antiPatternsSheet)

    def report_cache_without_expiry(self):

        # Worksheet 6 - [Cache Without Expiry]
        logger.info(
            '------------------- Cache Without Expiry -----------------------')
        cacheWithoutExpirySheet = self.workbook.add_worksheet(
            name='Cache Without Expiry')

        # Headings
        self.qualification_report_heading(
            cache_without_expiry_mapping["headers"], cacheWithoutExpirySheet)

        orgConfig = self.export_data.get('orgConfig')
        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            CacheWithoutExpiry = values['qualification']['CacheWithoutExpiry']
            for policy, value in CacheWithoutExpiry.items():
                col = 0
                cacheWithoutExpirySheet.write(row, col, self.orgName)
                col += 1
                cacheWithoutExpirySheet.write(row, col, proxy)
                col += 1
                cacheWithoutExpirySheet.write(row, col, policy)
                col += 1
                cacheWithoutExpirySheet.write(row, col, value)

                row += 1

        cacheWithoutExpirySheet.autofit()
        # Info block
        self.qualification_report_info_box(
            cache_without_expiry_mapping, cacheWithoutExpirySheet)

    def report_apps_without_api_products(self):

        # Worksheet 7 - [Apps Without ApiProducts]
        logger.info(
            '------------------- Apps Without ApiProducts -----------------------')
        appsWithoutAPIProductsSheet = self.workbook.add_worksheet(
            name='Apps Without ApiProducts')

        # Headings
        self.qualification_report_heading(
            apps_without_api_products_mapping["headers"], appsWithoutAPIProductsSheet)

        orgConfig = self.export_data.get('orgConfig')
        row = 1

        apps = orgConfig['apps']
        for app, value in apps.items():
            products = value['credentials'][0]['apiProducts']
            if len(products) == 0:
                col = 0
                appsWithoutAPIProductsSheet.write(row, col, self.orgName)
                # app name
                col += 1
                appsWithoutAPIProductsSheet.write(row, col, value['name'])
                # id
                col += 1
                appsWithoutAPIProductsSheet.write(row, col, app)
                # status
                col += 1
                appsWithoutAPIProductsSheet.write(
                    row, col, value['credentials'][0]['status'])

        appsWithoutAPIProductsSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            apps_without_api_products_mapping, appsWithoutAPIProductsSheet)

    def report_json_path_enabled(self):

        # Worksheet 8 - [Json Path Enabled]
        logger.info(
            '------------------- Json Path Enabled -----------------------')
        jsonPathEnabledSheet = self.workbook.add_worksheet(
            name='Json Path Enabled')

        # Headings
        self.qualification_report_heading(
            json_path_enabled_mapping["headers"], jsonPathEnabledSheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            JsonPathEnabled = values['qualification']['JsonPathEnabled']

            for policy, value in JsonPathEnabled.items():
                col = 0
                jsonPathEnabledSheet.write(row, col, self.orgName)
                col += 1
                jsonPathEnabledSheet.write(row, col, proxy)
                col += 1
                jsonPathEnabledSheet.write(row, col, policy)
                col += 1
                jsonPathEnabledSheet.write(row, col, value)

                row += 1

        jsonPathEnabledSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            json_path_enabled_mapping, jsonPathEnabledSheet)

    def report_cname_anomaly(self):

        # Worksheet 9 - [CName Anomaly]
        logger.info('------------------- CName Anomaly -----------------------')
        cnameAnamoly = self.workbook.add_worksheet(name='CName Anomaly')

        # Headings
        self.qualification_report_heading(
            cname_anomaly_mapping["headers"], cnameAnamoly)

        envConfig = self.export_data.get('envConfig')
        row = 1

        for key, value in envConfig.items():
            vhosts = value['vhosts']
            for vhost in vhosts:
                if vhosts[vhost]['useBuiltInFreeTrialCert']:
                    # org name
                    col = 0
                    cnameAnamoly.write(row, col, self.orgName)
                    # Env name
                    col += 1
                    cnameAnamoly.write(row, col, key)
                    col += 1
                    cnameAnamoly.write(row, col, vhosts[vhost]['name'])
                    row += 1

        cnameAnamoly.autofit()
        # Info block
        self.qualification_report_info_box(cname_anomaly_mapping, cnameAnamoly)

    def report_unsupported_policies(self):

        # Worksheet 10 - [Unsupported Policies]
        logger.info(
            '------------------- Unsupported Policies -----------------------')
        unsupportedPolicesSheet = self.workbook.add_worksheet(
            name='Unsupported Policies')

        # Headings
        self.qualification_report_heading(
            unsupported_polices_mapping["headers"], unsupportedPolicesSheet)

        orgConfig = self.export_data.get('orgConfig')
        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            policies = values['qualification']['policies']
            for policy_name, policy in policies.items():
                col = 0
                unsupportedPolicesSheet.write(row, col, self.orgName)
                col += 1
                unsupportedPolicesSheet.write(row, col, proxy)
                col += 1
                unsupportedPolicesSheet.write(row, col, policy_name)
                col += 1
                unsupportedPolicesSheet.write(row, col, policy)

                row += 1

        unsupportedPolicesSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            unsupported_polices_mapping, unsupportedPolicesSheet)

    def report_api_limits(self):

        # Worksheet 12 - [Product Limits - API Limits]
        logger.info(
            '------------------- Product Limits - API Limits -----------------------')
        apiLimitsSheet = self.workbook.add_worksheet(
            name='Product Limits - API Limits')

        # Headings
        self.qualification_report_heading(
            api_limits_mapping["headers"], apiLimitsSheet)

        allowed_no_of_revisions_per_proxy = self.backend_cfg.get(
            'inputs', 'NO_OF_API_REVISIONS_IN_API_PROXY')
        orgConfig = self.export_data.get('orgConfig')
        row = 1

        for key, value in orgConfig['apis'].items():
            # Org name
            col = 0
            apiLimitsSheet.write(row, col, self.orgName)
            # Api name
            col += 1
            apiLimitsSheet.write(row, col, key)
            # Revisions
            col += 1
            if len(value) > int(allowed_no_of_revisions_per_proxy):
                apiLimitsSheet.write(row, col, len(value), self.danger_format)
            else:
                apiLimitsSheet.write(row, col, len(value))
            row += 1

        apiLimitsSheet.autofit()
        # Info block
        self.qualification_report_info_box(api_limits_mapping, apiLimitsSheet)

    def report_org_limits(self):

        # Worksheet 13 - [Product Limits - Org Limits]
        logger.info(
            '------------------- Product Limits - Org Limits -----------------------')
        orgLimitsSheet = self.workbook.add_worksheet(
            name='Product Limits - Org Limits')
        allowed_no_of_kvms_per_org = self.backend_cfg.get(
            'inputs', 'NO_OF_KVMS_PER_ORG')

        # Headings
        self.qualification_report_heading(
            org_limits_mapping["headers"], orgLimitsSheet)

        orgConfig = self.export_data.get('orgConfig')
        row = 1

        # Org name
        col = 0
        orgLimitsSheet.write(row, col, self.orgName)
        # Developer count
        col += 1
        orgLimitsSheet.write(row, col, len(orgConfig['developers']))
        # KVM count
        col += 1
        if len(orgConfig['kvms']) > int(allowed_no_of_kvms_per_org):
            orgLimitsSheet.write(row, col, len(
                orgConfig['kvms']), self.danger_format)
        else:
            orgLimitsSheet.write(row, col, len(orgConfig['kvms']))

        orgLimitsSheet.autofit()
        # Info block
        self.qualification_report_info_box(org_limits_mapping, orgLimitsSheet)

    def report_env_limits(self):

        # Worksheet 14 - [Product Limits - Env Limits]
        logger.info(
            '------------------- Product Limits - Env Limits -----------------------')
        envLimitsSheet = self.workbook.add_worksheet(
            name='Product Limits - Env Limits')

        allowed_no_of_kvms_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_KVMS_PER_ENV')
        allowed_no_of_target_servers_per_env = self.backend_cfg.get(
            'inputs', 'NO_OF_TARGET_SERVERS_PER_ENV')

        # Headings
        self.qualification_report_heading(
            env_limits_mapping["headers"], envLimitsSheet)

        envConfig = self.export_data.get('envConfig')
        row = 1

        for key, value in envConfig.items():
            # Org name
            col = 0
            envLimitsSheet.write(row, col, self.orgName)
            # Env name
            col += 1
            envLimitsSheet.write(row, col, key)
            # Target servers
            col += 1
            if len(value['targetServers']) > int(allowed_no_of_target_servers_per_env):
                envLimitsSheet.write(row, col, len(
                    value['targetServers']), self.danger_format)
            else:
                envLimitsSheet.write(row, col, len(value['targetServers']))
            # Caches
            col += 1
            envLimitsSheet.write(row, col, len(value['caches']))
            # Certs
            col += 1
            certs = 0
            for keystore, keystorecontent in value['keystores'].items():
                certs = certs + len(keystorecontent['certs'])
            envLimitsSheet.write(row, col, certs)
            # KVMs
            col += 1
            if len(value['kvms']) > int(allowed_no_of_kvms_per_env):
                envLimitsSheet.write(row, col, len(
                    value['kvms']), self.danger_format)
            else:
                envLimitsSheet.write(row, col, len(value['kvms']))
            # Virtual hosts
            col += 1
            envLimitsSheet.write(row, col, len(value['vhosts']))
            row += 1

        envLimitsSheet.autofit()
        # Info block
        self.qualification_report_info_box(env_limits_mapping, envLimitsSheet)

    def report_api_with_multiple_basepaths(self):

        # Worksheet 15 - [APIs With Multiple BasePaths]
        logger.info(
            '------------------- APIs With Multiple BasePaths -----------------------')
        apiWithMultipleBasepathsSheet = self.workbook.add_worksheet(
            name='APIs With Multiple BasePaths')

        # Headings
        self.qualification_report_heading(
            api_with_multiple_basepath_mapping["headers"], apiWithMultipleBasepathsSheet)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("unifier_created"):
                continue

            base_paths = values['qualification']['base_paths']
            base_paths = [
                str(path) if path is not None else 'None' for path in base_paths]
            col = 0
            apiWithMultipleBasepathsSheet.write(row, col, self.orgName)
            col += 1
            apiWithMultipleBasepathsSheet.write(row, col, proxy)
            col += 1
            if len(base_paths) > 5:
                apiWithMultipleBasepathsSheet.write(
                    row, col, '\n'.join(base_paths), self.danger_format)
            elif len(base_paths) > 1:
                apiWithMultipleBasepathsSheet.write(
                    row, col, '\n'.join(base_paths), self.yellow_format)
            elif len(base_paths) == 1:
                apiWithMultipleBasepathsSheet.write(
                    row, col, '\n'.join(base_paths))

            row += 1

        apiWithMultipleBasepathsSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            api_with_multiple_basepath_mapping, apiWithMultipleBasepathsSheet)

    def sharding(self):

        # Worksheet 11 - [Sharded envs]
        logger.info(
            '------------------- Sharded Env Info -----------------------')
        shardingOutput = self.workbook.add_worksheet(
            name='Target Environments')

        # Headings
        self.qualification_report_heading(
            sharding_output["headers"], shardingOutput)

        sharding_env_output = self.export_data.get('sharding_output')
        row = 1

        for env, sharded_envs in sharding_env_output.items():
            for sharded_env, content in sharded_envs.items():
                col = 0
                shardingOutput.write(row, col, self.orgName)
                col += 1
                shardingOutput.write(row, col, env)
                col += 1
                shardingOutput.write(row, col, sharded_env)
                col += 1
                proxies_list = content.get("proxyname", [])
                shardingOutput.write(row, col, '\n'.join(proxies_list))
                col += 1
                shared_flows_list = content.get("shared_flow", [])
                shardingOutput.write(row, col, '\n'.join(shared_flows_list))
                col += 1
                shardingOutput.write(row, col, len(proxies_list))
                col += 1
                shardingOutput.write(row, col, len(shared_flows_list))
                col += 1
                shardingOutput.write(row, col, len(
                    proxies_list) + len(shared_flows_list))
                row += 1

        shardingOutput.autofit()
        # Info block
        self.qualification_report_info_box(sharding_output, shardingOutput)

    def report_alias_keycert(self):
        logger.info(
            '------------------- Aliases with private keys -----------------------')
        aliasesWithPrivateKeys = self.workbook.add_worksheet(
            name='Aliases with private keys')

        # Headings
        self.qualification_report_heading(
            aliases_with_private_keys["headers"], aliasesWithPrivateKeys)

        row = 1
        for env, content in self.export_data['envConfig'].items():
            for keystore, keystore_content in content.get('keystores').items():
                if keystore_content.get('alias_data'):
                    for alias, alias_content in keystore_content.get('alias_data').items():
                        col = 0
                        aliasesWithPrivateKeys.write(row, col, self.orgName)
                        col += 1
                        aliasesWithPrivateKeys.write(row, col, env)
                        col += 1
                        aliasesWithPrivateKeys.write(row, col, keystore)
                        col += 1
                        aliasesWithPrivateKeys.write(row, col, alias)
                        col += 1
                        if alias_content.get('keyName'):
                            aliasesWithPrivateKeys.write(
                                row, col, alias_content.get('keyName'), self.danger_format)
                        row += 1
        aliasesWithPrivateKeys.autofit()
        # Info block
        self.qualification_report_info_box(
            aliases_with_private_keys, aliasesWithPrivateKeys)

    def sharded_proxies(self):
        logger.info(
            '------------------- Sharded Proxies -----------------------')
        ShardedProxies = self.workbook.add_worksheet(name='Sharded Proxies')

        # Headings
        self.qualification_report_heading(
            sharded_proxies["headers"], ShardedProxies)

        row = 1

        proxy_map = self.export_data['proxy_dependency_map']
        for proxy, values in proxy_map.items():
            if values.get("is_split"):
                sharded_proxies_list = values.get("split_output_names")
                col = 0
                ShardedProxies.write(row, col, self.orgName)
                col += 1
                ShardedProxies.write(row, col, proxy)
                col += 1
                ShardedProxies.write(row, col, '\n'.join(sharded_proxies_list))
                row += 1

        ShardedProxies.autofit()
        # Info block
        self.qualification_report_info_box(sharded_proxies, ShardedProxies)

    def report_org_resourcefiles(self):

        logger.info(
            '------------------- Org level Resourcefiles -----------------------')
        OrgResourcefilesSheet = self.workbook.add_worksheet(
            name='Org Level Resourcefiles')

        # Headings
        self.qualification_report_heading(
            org_resourcefiles["headers"], OrgResourcefilesSheet)

        row = 1

        for key, value in self.export_data['orgConfig']["resourcefiles"].items():
            col = 0
            OrgResourcefilesSheet.write(row, col, self.orgName)
            col += 1
            OrgResourcefilesSheet.write(row, col, key)

            row += 1
        OrgResourcefilesSheet.autofit()
        # Info block
        self.qualification_report_info_box(
            org_resourcefiles, OrgResourcefilesSheet)

    def report_network_topology(self):
        # Worksheet 16 - [Apigee OPDK/Edge (4G) components]
        logger.info(
            '------------------- Apigee OPDK/Edge (4G) components -----------------------')
        topologyInstallationSheet = self.workbook.add_worksheet(
            name='Apigee (4G) components')

        # Headings
        self.qualification_report_heading(
            topology_installation_mapping["headers"], topologyInstallationSheet)

        row = 1

        if len(self.topology_mapping) != 0:
            for dc in self.topology_mapping['data_center_mapping']:

                for pod in self.topology_mapping['data_center_mapping'][dc]:

                    for pod_instance in self.topology_mapping['data_center_mapping'][dc][pod]:
                        col = 0
                        topologyInstallationSheet.write(row, col, dc)
                        col += 1
                        topologyInstallationSheet.write(row, col, pod)
                        col += 1

                        topologyInstallationSheet.write(
                            row, col, '\n'.join(pod_instance['type']))
                        col += 1

                        for col_key_map in topology_installation_mapping["key_mapping"]:
                            topologyInstallationSheet.write(
                                row, col, pod_instance[col_key_map])
                            col += 1

                        row += 1
        topologyInstallationSheet.autofit()

    def qualification_report_summary(self):

        # Worksheet 15 - [Qualification Summary]
        logger.info(
            '------------------- Qualification Summary -----------------------')
        qualificationSummarySheet = self.workbook.add_worksheet(
            name='Qualification Summary')

        col = 0
        qualificationSummarySheet.set_column(
            col, col+1, int(report_summary["col_width"])+1)
        qualificationSummarySheet.merge_range(
            f'A{report_summary["header_row"]}:B{report_summary["header_row"]}', report_summary["header_text"], self.summary_main_header_format)

        row = report_summary["header_row"]+1

        for block in report_summary["blocks"]:

            if "APIGEE_SOURCE" in block and self.cfg.get('inputs', 'SOURCE_APIGEE_VERSION') != block["APIGEE_SOURCE"]:
                break

            qualificationSummarySheet.merge_range(
                f'A{row}:B{row}', block["header"], self.summary_block_header_format)
            row = row+1

            col = 0
            for row_sheet in block["sheets"]:
                if ("link_of_text" in row_sheet):
                    qualificationSummarySheet.write_url(
                        f'A{row}', row_sheet["link_of_text"], self.summary_link_format, string=row_sheet["text_col"])
                else:
                    qualificationSummarySheet.write(
                        row-1, col, row_sheet["text_col"], self.summary_format)

                qualificationSummarySheet.write_formula(
                    f'B{row}', row_sheet["result_col"], cell_format=self.summary_format)

                qualificationSummarySheet.conditional_format(f'B{row}:B{row}', {
                    'type': 'text',
                    'criteria': 'containing',
                    'value': 'PASSED',
                    'format': self.summary_cell_green_format
                })
                qualificationSummarySheet.conditional_format(f'B{row}:B{row}', {
                    'type': 'text',
                    'criteria': 'containing',
                    'value': 'FAILED',
                    'format': self.summary_cell_danger_format
                })
                row = row+1

        self.summary_note_blue_format.set_text_wrap()
        self.summary_note_green_format.set_text_wrap()

        row = row+report_summary["note_list"]["skip_rows"]
        col = 0
        for note in report_summary["note_list"]["notes"]:
            if (note["bg_color"] == "blue"):
                qualificationSummarySheet.merge_range(
                    f'A{row}:B{row}', note["text"], self.summary_note_blue_format)
            else:
                qualificationSummarySheet.merge_range(
                    f'A{row}:B{row}', note["text"], self.summary_note_green_format)
            row = row+1

    def reverse_sheets(self):
        self.workbook.worksheets().reverse()

    def close(self):
        # Close the workbook
        self.workbook.close()
