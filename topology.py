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

"""Generates and visualizes Apigee topology diagrams.

This module interacts with the Apigee Management API to retrieve topology
information, including pod and component details.
It then processes this information to create data center mappings and
generates visual representations of the topology using diagrams.
"""
import os
from diagrams import Diagram, Cluster  # noqa pylint: disable=E0401
from diagrams.generic.blank import Blank  # noqa pylint: disable=E0401
from classic import ApigeeClassic
from topology_mapping.pod import pod_mapping
from utils import write_json
from base_logger import logger


class ApigeeTopology():
    """Represents and visualizes Apigee topology.

    Retrieves topology information from Apigee, creates data center
    mappings, and generates topology diagrams.
    """

    def __init__(self, baseurl, org, token, auth_type, cfg):  # noqa pylint: disable=R0913,R0917
        """Initializes ApigeeTopology.

        Args:
            baseurl (str): The base URL for the Apigee Management API.
            org (str): The Apigee organization name.
            token (str): The authentication token.
            auth_type (str): The authentication type.
            cfg (configparser.ConfigParser): The configuration object.
        """
        self.baseurl = baseurl
        self.org = org
        self.token = token
        self.auth_type = auth_type
        self.cfg = cfg

        target_dir = self.cfg.get('inputs', 'TARGET_DIR')
        topology_dir = self.cfg.get('topology', 'TOPOLOGY_DIR')

        self.topology_dir_path = f"{target_dir}/{topology_dir}"

        if not os.path.isdir(self.topology_dir_path):
            os.makedirs(self.topology_dir_path)
        try:
            ssl_verification = cfg.getboolean('inputs', 'SSL_VERIFICATION')
        except ValueError:
            ssl_verification = True
        self.opdk = ApigeeClassic(baseurl, org, token, self.auth_type, ssl_verification)  # noqa pylint: disable=C0301

    def get_topology_mapping(self):
        """Retrieves and maps Apigee topology components.

        Retrieves pod and component details from the Apigee Management API
            and creates a mapping.

        Returns:
            dict: A dictionary containing the topology mapping.
        """

        logger.info('In get APIGEE edge network topology mapping')
        pod_component_result = {}

        for pod_name in pod_mapping:
            component_type_resp = []
            result_arr = self.opdk.view_pod_component_details(pod_name)

            for result in result_arr:
                component_type_resp.append({
                    "externalHostName": result["externalHostName"] if "externalHostName" in result else "",  # noqa pylint: disable=C0301
                    "externalIP": result["externalIP"] if "externalIP" in result else "",  # noqa
                    "internalHostName": result["internalHostName"] if "internalHostName" in result else "",  # noqa pylint: disable=C0301
                    "internalIP": result["internalIP"] if "internalIP" in result else "",  # noqa
                    "isUp": result["isUp"] if "isUp" in result else "",
                    "pod": result["pod"] if "pod" in result else "",
                    "reachable": result["reachable"] if "reachable" in result else "",  # noqa
                    "region": result["region"] if "region" in result else "",  # noqa
                    "type": result["type"] if "type" in result else ""
                })

            pod_component_result[f'{pod_name}'] = component_type_resp

        nw_toplogy_mapping = self.cfg.get('topology', 'NW_TOPOLOGY_MAPPING')  # noqa
        write_json(
            f"{self.topology_dir_path}/{nw_toplogy_mapping}", pod_component_result)  # noqa

        return pod_component_result

    def get_data_center_mapping(self, pod_component_mapping):
        """Creates a data center mapping from pod component information.

        Processes the pod component mapping to create a data center mapping.

        Args:
            pod_component_mapping (dict): The pod component mapping.

        Returns:
            dict: A dictionary containing the data center mapping.
        """

        logger.info('In get data center mapping from network topology mapping')  # noqa
        data_center = {}

        for pod in pod_component_mapping:
            for component_instance in pod_component_mapping[pod]:

                if component_instance['region'] not in data_center:
                    data_center[component_instance['region']] = {}

                if component_instance['pod'] not in data_center[component_instance['region']]:  # noqa pylint: disable=C0301
                    data_center[component_instance['region']
                                ][component_instance['pod']] = []

                data_center[component_instance['region']][component_instance['pod']].append(  # noqa pylint: disable=C0301
                    component_instance)

        datacenter_mapping = self.cfg.get('topology', 'DATA_CENTER_MAPPING')  # noqa
        write_json(
            f'{self.topology_dir_path}/{datacenter_mapping}', data_center)  # noqa

        return data_center

    def draw_topology_graph_diagram(self, data_center):  # noqa pylint: disable=R0914,R0912
        """Draws a topology graph diagram.

        Generates a visual representation of the Apigee topology
        using diagrams.

        Args:
            data_center (dict): The data center mapping.
        """

        logger.info('Draw network topology mapping graph diagram')
        main_graph_attr = {
            "nodesep": "1",
            "fontsize": "70",
        }

        data_center_attr = {
            "bgcolor": "#f3f3f3",
            "style": "ortho",
            "ranksep": "1",
            "fontsize": "25",
        }

        pod_attr = {
            "fontsize": "30",
        }

        ip_attr = {
            "nodesep": "1",
            "fontsize": "25",
        }
        with Diagram("Edge Installation Topology with Pod and IP Clustering", filename=f"{self.topology_dir_path}/Edge_Installation_Topology_With_Pod_IPs", show=False, graph_attr=main_graph_attr, node_attr=main_graph_attr, outformat=["png"]):  # noqa pylint: disable=C0301
            internal_ip_clusters = {}
            for dc in data_center:
                with Cluster(dc, graph_attr=data_center_attr):
                    for pod in data_center[dc]:
                        with Cluster(pod, graph_attr=pod_attr):
                            for pod_instance in data_center[dc][pod]:
                                if not pod_instance['internalIP'] in internal_ip_clusters:  # noqa
                                    internal_ip_clusters[pod_instance['internalIP']] = [  # noqa
                                    ]
                                internal_ip_clusters[pod_instance['internalIP']].append(  # noqa
                                    pod_instance)

                            svc_group = []
                            for ip_grp, ip_grp_value in internal_ip_clusters.items():       # noqa pylint: disable=C0301
                                ip_attr['bgcolor'] = pod_mapping[pod]["bgcolor"]  # noqa
                                with Cluster(ip_grp, graph_attr=ip_attr):  # noqa
                                    for int_ip in ip_grp_value:  # noqa
                                        for component in int_ip['type']:  # noqa
                                            svc_group.append(
                                                Blank(f"{component}", height="0.0001", width="20", fontsize="35"))    # noqa pylint: disable=C0301

        with Diagram("Edge Installation Topology with IPs Clustering", filename=f"{self.topology_dir_path}/Edge_Installation_Topology_With_IPs", show=False, graph_attr=main_graph_attr, node_attr=main_graph_attr, outformat=["png"]):  # noqa pylint: disable=C0301
            internal_ip_clusters = {}
            for dc in data_center:
                with Cluster(dc, graph_attr=data_center_attr):
                    for pod in data_center[dc]:
                        for pod_instance in data_center[dc][pod]:
                            if not pod_instance['internalIP'] in internal_ip_clusters:  # noqa
                                internal_ip_clusters[pod_instance['internalIP']] = [  # noqa
                                ]
                            internal_ip_clusters[pod_instance['internalIP']].append(  # noqa
                                pod_instance)

                    svc_group = []
                    for ip_grp, ip_grp_value in internal_ip_clusters.items():
                        with Cluster(ip_grp, graph_attr=ip_attr):
                            for int_ip in ip_grp_value:  # noqa
                                for component in int_ip['type']:
                                    svc_group.append(
                                        Blank(f"{component}", height="0.0001", width="20", fontsize="35"))  # noqa pylint: disable=C0301
