#!/usr/bin/python

# Copyright 2024 Google LLC
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

from classic import ApigeeClassic
from topology_mapping.pod import pod_mapping
from utils import write_json
from diagrams import Diagram, Cluster
from diagrams.generic.blank import Blank
import os
from base_logger import logger


class ApigeeTopology():

    def __init__(self, baseurl, org, token, auth_type, cfg):
        self.baseurl = baseurl
        self.org = org
        self.token = token
        self.auth_type = auth_type
        self.cfg = cfg

        TARGET_DIR = self.cfg.get('inputs', 'TARGET_DIR')
        TOPOLOGY_DIR = self.cfg.get('topology', 'TOPOLOGY_DIR')

        self.topology_dir_path = f"{TARGET_DIR}/{TOPOLOGY_DIR}"

        if not os.path.isdir(self.topology_dir_path):
            os.makedirs(self.topology_dir_path)

        self.opdk = ApigeeClassic(baseurl, org, token, self.auth_type)

    def get_topology_mapping(self):

        logger.info('In get APIGEE edge network topology mapping')
        pod_component_result = {}

        for pod_name in pod_mapping:
            component_type_resp = []
            result_arr = self.opdk.view_pod_component_details(pod_name)

            for result in result_arr:
                component_type_resp.append({
                    "externalHostName": result["externalHostName"] if "externalHostName" in result else "",
                    "externalIP": result["externalIP"] if "externalIP" in result else "",
                    "internalHostName": result["internalHostName"] if "internalHostName" in result else "",
                    "internalIP": result["internalIP"] if "internalIP" in result else "",
                    "isUp": result["isUp"] if "isUp" in result else "",
                    "pod": result["pod"] if "pod" in result else "",
                    "reachable": result["reachable"] if "reachable" in result else "",
                    "region": result["region"] if "region" in result else "",
                    "type": result["type"] if "type" in result else ""
                })

            pod_component_result[f'{pod_name}'] = component_type_resp

        NW_TOPOLOGY_MAPPING = self.cfg.get('topology', 'NW_TOPOLOGY_MAPPING')
        write_json(
            f"{self.topology_dir_path}/{NW_TOPOLOGY_MAPPING}", pod_component_result)

        return pod_component_result

    def get_data_center_mapping(self, pod_component_mapping):

        logger.info('In get data center mapping from network topology mapping')
        data_center = {}

        for pod in pod_component_mapping:
            for component_instance in pod_component_mapping[pod]:

                if component_instance['region'] not in data_center:
                    data_center[component_instance['region']] = {}

                if component_instance['pod'] not in data_center[component_instance['region']]:
                    data_center[component_instance['region']
                                ][component_instance['pod']] = []

                data_center[component_instance['region']][component_instance['pod']].append(
                    component_instance)

        DATA_CENTER_MAPPING = self.cfg.get('topology', 'DATA_CENTER_MAPPING')
        write_json(
            f'{self.topology_dir_path}/{DATA_CENTER_MAPPING}', data_center)

        return data_center

    def draw_topology_graph_diagram(self, data_center):

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
        with Diagram(f"Edge Installation Topology with Pod and IP Clustering", filename=f"{self.topology_dir_path}/Edge_Installation_Topology_With_Pod_IPs", show=False, graph_attr=main_graph_attr, node_attr=main_graph_attr, outformat=["png"]):
            for dc in data_center:
                with Cluster(dc, graph_attr=data_center_attr):
                    for pod in data_center[dc]:
                        with Cluster(pod, graph_attr=pod_attr):
                            internalIPClusters = {}
                            for pod_instance in data_center[dc][pod]:
                                if not pod_instance['internalIP'] in internalIPClusters:
                                    internalIPClusters[pod_instance['internalIP']] = [
                                    ]
                                internalIPClusters[pod_instance['internalIP']].append(
                                    pod_instance)

                            svc_group = []
                            for internalIPGrp in internalIPClusters:
                                ip_attr['bgcolor'] = pod_mapping[pod]["bgcolor"]
                                with Cluster(internalIPGrp, graph_attr=ip_attr):
                                    for internalIP in internalIPClusters[internalIPGrp]:
                                        for component in internalIP['type']:
                                            svc_group.append(
                                                Blank(f"{component}", height="0.0001", width="20", fontsize="35"))

        with Diagram(f"Edge Installation Topology with IPs Clustering", filename=f"{self.topology_dir_path}/Edge_Installation_Topology_With_IPs", show=False, graph_attr=main_graph_attr, node_attr=main_graph_attr, outformat=["png"]):
            internalIPClusters = {}
            for dc in data_center:
                with Cluster(dc, graph_attr=data_center_attr):
                    for pod in data_center[dc]:
                        for pod_instance in data_center[dc][pod]:
                            if not pod_instance['internalIP'] in internalIPClusters:
                                internalIPClusters[pod_instance['internalIP']] = [
                                ]
                            internalIPClusters[pod_instance['internalIP']].append(
                                pod_instance)

                    svc_group = []
                    for internalIPGrp in internalIPClusters:
                        with Cluster(internalIPGrp, graph_attr=ip_attr):
                            for internalIP in internalIPClusters[internalIPGrp]:
                                for component in internalIP['type']:
                                    svc_group.append(
                                        Blank(f"{component}", height="0.0001", width="20", fontsize="35"))
