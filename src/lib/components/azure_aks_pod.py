import requests
from typing import Coroutine, Dict, Any
from lib.components.azure_base import AzureImpactNode
from lib.components.azure_aks_node import AKSNode
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.ief.core import *
from lib.auth.azure import AzureManagedIdentityAuthParams

from kubernetes import client, config
from kubernetes.config.kube_config import KubeConfigLoader

import yaml
import re
import io

import asyncio

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricAggregationType
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential

aggregation = MetricAggregationType.AVERAGE #for monitoring queries


class AKSPod(AzureImpactNode):
        def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval="PT5M", timespan="PT1H"):
            super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval, timespan)
            self.type = "akspod"
            self.name = name
            self.resources = []
            self.observations = {}
            self.credential = DefaultAzureCredential()
            self.resource_selectors = resource_selectors
            self.carbon_intensity_provider = carbon_intensity_provider
            self.metadata = metadata
            self.auth_object = auth_object
            self.inner_model = model if model is not None else ComputeServer_STATIC_IMP() #use to calculate the impact of the node
            subscription_id = self.resource_selectors.get("subscription_id", None)
            resource_group = self.resource_selectors.get("resource_group", None)
            cluster_name = self.resource_selectors.get("cluster_name", None)
            nodepool_name = self.resource_selectors.get("nodepool_name", None)
            self.prometheus_endpoint = self.resource_selectors.get("prometheus_endpoint", None)


        def list_supported_skus(self):
            pass
        
        async def lookup_static_params(self) -> Dict[str, Any]:
            return {}

        def get_auth_token(self):
            scope = "https://prometheus.monitor.azure.com/.default"
            token = self.credential.get_token(scope)
            return token.token


        async def query_prometheus(self, prometheus_endpoint: str, query: str,  interval: str, timespan: str) -> Dict[str, Any]:
            url = f"{prometheus_endpoint}/api/v1/query"
          
            #timespan = timespan.lower().replace("pt", "")
            #interval = self.interval.lower().replace("pt", "")
 
          
            params = {
                "query": query,
                "start": f"now()-{timespan}",
                "end": "now()",
                "step": interval
            }

            params = {"query" : query}
            auth_token = self.get_auth_token()
            headers = {
                "Accept": "application/json",
                'Authorization': f'Bearer %s' % auth_token,
                'Content-Type' : 'application/x-www-form-urlencoded'
            }

            response = requests.get(url, params=params, headers=headers)

            if response.status_code != 200:
                raise Exception(f"Failed to query Prometheus: {response.text}")

            return response.json()

        async def fetch_resources(self) -> Dict[str, Any]:

            subscription_id = self.resource_selectors.get("subscription_id", None)
            resource_group_name = self.resource_selectors.get("resource_group", None)
            cluster_name = self.resource_selectors.get("cluster_name", None)

            container_service_client = ContainerServiceClient(self.credential, subscription_id)
            
            kubeconfig = container_service_client.managed_clusters.list_cluster_user_credentials(resource_group_name, cluster_name).kubeconfigs[0].value

            kubeconfig_stream = io.BytesIO(kubeconfig)
            kubeconfig_dict = yaml.safe_load(kubeconfig_stream)
            

            # Load the Kubernetes configuration from the kubeconfig
            loader = KubeConfigLoader(config_dict=kubeconfig_dict)
            configuration = client.Configuration()
            loader.load_and_set(configuration)
            client.Configuration.set_default(configuration)
            
            v1 = client.CoreV1Api()
            pod_list = []

            if "namespace" in self.resource_selectors:
                namespace = self.resource_selectors["namespace"]
                pods = v1.list_namespaced_pod(namespace=namespace).items
            elif "label_selector" in self.resource_selectors:
                label_selector = self.resource_selectors["label_selector"]
                pods = v1.list_pod_for_all_namespaces(label_selector=label_selector).items
            else:
                pods = v1.list_pod_for_all_namespaces().items

            nodes_uris = {}
            for item in pods:
                pod = {}
                pod['name'] = item.metadata.name
                pod['namespace'] = item.metadata.namespace
                pod['labels'] = item.metadata.labels
                pod['node_name'] = item.spec.node_name

                # Get the CPU and memory requests and limits
                resources = item.spec.containers[0].resources
                if resources is not None:
                    requests = resources.requests
                    limits = resources.limits
                    if requests is not None:
                        pod['cpu_request'] = requests.get('cpu')
                        pod['memory_request'] = requests.get('memory')
                    if limits is not None:
                        pod['cpu_limit'] = limits.get('cpu')
                        pod['memory_limit'] = limits.get('memory')

                #Get host node info
                node_name = pod['node_name']
                if node_name not in nodes_uris:
                    node_uri = v1.read_node(node_name).spec.provider_id.replace("azure://", "")
                    nodes_uris[node_name] = node_uri
                pod['node_uri'] = nodes_uris[node_name]
                pod['uri'] = item.metadata.uid
                pod_list.append(pod)
            

            self.resources = pod_list
            return self.resources
        
        def cpu_to_gb(self, cpu: str) -> float:
            """
            Convert CPU requests and limits to GB.
            :param cpu: str, CPU requests or limits, e.g. '100m', '1'.
            :return: float, CPU requests or limits in GB.
            """
            if cpu is None:
                Warning("Pod CPU limit is None ; using default value of 1")
                return 1 # default value
            cpu = str(cpu)
            if cpu.endswith('m'):
                return float(cpu[:-1]) / 1000
            else:
                return float(cpu)

        def memory_to_gb(self, memory: str) -> float:
            """
            Convert memory requests and limits to GB.
            :param memory: str, memory requests or limits, e.g. '64Mi', '1Gi'.
            :return: float, memory requests or limits in GB.
            """
            if memory is None:
                Warning("Pod memory limit is None ; using default value of 1")
                return 1
            memory = str(memory)
            if memory.endswith('Ki'):
                return float(memory[:-2]) / (1024 ** 2)
            elif memory.endswith('Mi'):
                return float(memory[:-2]) / 1024
            elif memory.endswith('Gi'):
                return float(memory[:-2])
            elif memory.endswith('Ti'):
                return float(memory[:-2]) * 1024
            elif memory.endswith('Pi'):
                return float(memory[:-2]) * (1024 ** 2)
            elif memory.endswith('Ei'):
                return float(memory[:-2]) * (1024 ** 3)
            elif memory.endswith('M'):
                return float(memory[:-1]) / 1024
            elif memory.endswith('G'):
                return float(memory[:-1])
            else:
                return float(memory) / (1024 ** 3)


        async def lookup_static_params(self) -> Dict[str, Any]:
            pod_static_params = {}
            
            if not self.resources or self.resources == {}:
                await self.fetch_resources()
            pods_list = self.resources

            # get CPU & RAM, requests & limits for each pod, in GB
            for pod in pods_list:
                print(pod)
                pod_name = pod['name']
                pod_static_params[pod_name] = {}
                pod_static_params[pod_name]['cpu_request'] = pod.get('cpu_request', 0)
                pod_static_params[pod_name]['cpu_limit'] = pod.get('cpu_limit', 0)
                pod_static_params[pod_name]['memory_request'] = pod.get('memory_request', 0)
                pod_static_params[pod_name]['memory_limit'] = pod.get('memory_limit', 0)
                pod_static_params[pod_name]['uri'] = pod.get('uri', 0)

                #convert to GB
                pod_static_params[pod_name]['cpu_request'] = self.cpu_to_gb(pod_static_params[pod_name]['cpu_request'])
                pod_static_params[pod_name]['cpu_limit'] = self.cpu_to_gb(pod_static_params[pod_name]['cpu_limit'])
                pod_static_params[pod_name]['memory_request'] = self.memory_to_gb(pod_static_params[pod_name]['memory_request'])
                pod_static_params[pod_name]['memory_limit'] = self.memory_to_gb(pod_static_params[pod_name]['memory_limit'])
            
            return pod_static_params

        async def fetch_cpu_usage(self) -> Dict[str, float]:
            pod_names = '|'.join(pod['name'] for pod in self.resources)

            timespan = self.timespan.lower().replace("pt", "")
            interval = self.interval.lower().replace("pt", "")
 
            pod_node_cpu_usage = f'sum by (pod, node) (rate(container_cpu_usage_seconds_total[{timespan}])) / on (node) group_left sum by (node) (rate(container_cpu_usage_seconds_total[{timespan}])) * 100'
            print(pod_node_cpu_usage)
            pod_node_cpu_usage_metrics = await self.query_prometheus(self.prometheus_endpoint, pod_node_cpu_usage, interval, timespan)
            cpu_utilization = {}
            if pod_node_cpu_usage_metrics['status'] == 'success':
                data = pod_node_cpu_usage_metrics['data']['result']
                for pod in data:
                    if 'pod' not in pod['metric']:
                        pod_name = "non_pod_cpu_usage"
                    else:
                        pod_name = pod['metric']['pod']
                    cpu_usage = pod['value'][1]
                    cpu_utilization[pod_name] = float(cpu_usage)
            return cpu_utilization

        async def fetch_memory_usage(self) -> Dict[str, float]:
            pod_names = '|'.join(pod['name'] for pod in self.resources)
           
            timespan = self.timespan.lower().replace("pt", "")
            interval = self.interval.lower().replace("pt", "")
 
            pod_node_memory_usage = f'sum by (pod, node) (avg_over_time(container_memory_working_set_bytes[{timespan}])) / on (node) group_left sum by (node) (avg_over_time(container_memory_working_set_bytes[{timespan}])) * 100'
            print(pod_node_memory_usage)
            pod_node_memory_usage_metrics = await self.query_prometheus(self.prometheus_endpoint,pod_node_memory_usage, interval, timespan)
            memory_utilization = {}
            if pod_node_memory_usage_metrics['status'] == 'success':
                data = pod_node_memory_usage_metrics['data']['result']
                for pod in data:
                    if 'pod' not in pod['metric']:
                        pod_name = "non_pod_memory_usage"
                    else:
                        pod_name = pod['metric']['pod']
                    memory_usage = pod['value'][1]
                    if float(memory_usage) < 0:
                        memory_usage = 0
                    memory_utilization[pod_name] = float(memory_usage)
            return memory_utilization

        async def fetch_observations(self) -> Dict[str, Any]:
            cpu_utilization = await self.fetch_cpu_usage()
            memory_utilization = await self.fetch_memory_usage()
            observations = {}
            for pod in self.resources:
                if pod['name'] in cpu_utilization.keys():
                    cpu = cpu_utilization[pod['name']]
                else:
                    cpu = 0
                if pod['name'] in memory_utilization.keys():
                    memory = memory_utilization[pod['name']]
                else:
                    memory = 0
                observations[pod['name']] = {
                    'node_host_cpu_util_percent': float(cpu),
                    'node_host_memory_util_percent': float(memory),
                    'node_host_gpu_util_percent': 0  # gpu_utilization TODO
                }
            self.observations = observations
            return self.observations




        async def calculate(self, carbon_intensity = 100) -> Dict[str, SCIImpactMetricsInterface]:
            if self.resources == {} or self.resources == None:
                await self.fetch_resources()
            pod_list = self.resources

            pod_observations = await self.fetch_observations()
            pod_static_params = await self.lookup_static_params()

            node_names = set([pod['node_name'] for pod in pod_list])

            # first we gather the infos for the nodes: models, static params, impacts
            node_tasks = []
            node_static_params_tasks = []
            node_impact_metrics = {}
            node_static_params = {}
            node_models = {}
            for node_name in node_names:
                # create an AKSNode object for each node
                resource_selectors = {
                    "subscription_id": self.resource_selectors.get("subscription_id", None),
                    "resource_group": self.resource_selectors.get("resource_group", None),
                    "cluster_name": self.resource_selectors.get("cluster_name", None),
                    "node_name" : node_name,
                    "prometheus_endpoint": self.resource_selectors.get("prometheus_endpoint", None)
                }
                node = AKSNode(name = node_name, model = self.inner_model,  carbon_intensity_provider=self.carbon_intensity_provider, auth_object=self.auth_object, resource_selectors=resource_selectors, metadata=self.metadata)
                
                node_models[node_name] = node.inner_model

                node_task = asyncio.create_task(node.calculate())
                node_static_param_task = asyncio.create_task(node.lookup_static_params())


                node_tasks.append(node_task)
                node_static_params_tasks.append(node_static_param_task)

            node_static_params_results = await asyncio.gather(*node_static_params_tasks)
            node_results = await asyncio.gather(*node_tasks)

            for i, node_name in enumerate(node_names):
                node_static_params[node_name] = node_static_params_results[i]
                node_impact_metrics[node_name] = node_results[i]


            # now we create an AttributedImpactNodeInterface object for each pod
            # the AttributedImpactNodeInterface class is used to calculate the impact of a pod that shares node resources with other pods
            pod_tasks = []
            pods_impact = {}

            for pod in pod_list:
                node_name = pod['node_name']
                pod_name = pod['name']
                pod_impact_object = AttributedImpactNodeInterface(name = pod_name,
                                                                    host_node_impact_dict= node_impact_metrics[node_name],
                                                                    carbon_intensity_provider=self.carbon_intensity_provider,
                                                                    metadata=self.metadata,
                                                                    observations=pod_observations[pod_name],
                                                                    timespan=self.timespan,
                                                                    interval=self.interval,
                                                                    static_params = pod_static_params[pod_name],
                                                                    host_node_static_params=node_static_params[node_name],
                                                                    host_node_model = node_models[node_name])
                pod_task = asyncio.create_task(pod_impact_object.calculate())
                pod_tasks.append(pod_task)

            pod_results = await asyncio.gather(*pod_tasks)

            for i, pod in enumerate(pod_list):
                pod_name = pod['name']
                pods_impact[pod_name] = pod_results[i][pod_name] or {}

            return pods_impact
