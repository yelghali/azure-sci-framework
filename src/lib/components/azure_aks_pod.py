import requests
from typing import Dict, Any
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
        
        def get_auth_token(self):
            scope = "https://prometheus.monitor.azure.com/.default"
            token = self.credential.get_token(scope)
            return token.token


        def query_prometheus(self, prometheus_endpoint: str, query: str,  interval: str, timespan: str) -> Dict[str, Any]:
            url = f"{prometheus_endpoint}/api/v1/query"
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
                node_name = pod['node_name']
                if node_name not in nodes_uris:
                    node_uri = v1.read_node(node_name).spec.provider_id.replace("azure://", "")
                    nodes_uris[node_name] = node_uri
                pod['node_uri'] = nodes_uris[node_name]
                pod['uri'] = item.metadata.uid
                pod_list.append(pod)
            

            self.resources = pod_list
            return self.resources
        

        async def fetch_observations(self, aggregation: str = MetricAggregationType.AVERAGE, timespan: str = "PT1H", interval: str = "PT15M") -> Dict[str, Any]:
            self.subscription_id = self.resource_selectors.get("subscription_id", None)
            self.resource_group_name = self.resource_selectors.get("resource_group", None)
            monitor_client = MonitorManagementClient(self.credential, self.subscription_id)
            nodes = {}
            pod_list = self.resources


            timespan = self.timespan.lower().replace("pt", "")
            interval = self.interval.lower().replace("pt", "")
 
            observations = {}   

            cpu_utilization = {}
            memory_utilization = {}
            gpu_utilization = {}


            # Define the Prometheus queries to get CPU utilization percentage, total RAM, and GPU utilization percentage by node
            #pod_node_cpu_usage = f'sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate{{node=~"{node_name}"}}) by (pod)'


            pod_names = '|'.join( pod['name'] for pod in pod_list)

            # Define the Prometheus query to get the CPU usage of pods by node
            #pod_node_cpu_usage = f'sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate{{pod=~"{pod_names}"}}) by (pod)'
            
            #pod_node_cpu_usage = f'sum by (pod, node) (rate(container_cpu_usage_seconds_total{{pod=~"{pod_names}"}}["{timespan}"])) / on (node) group_left sum by (node) (rate(container_cpu_usage_seconds_total{{pod=~"{pod_names}"}}["{timespan}"])) * 100'
            #pod_node_cpu_usage = f'sum by (pod, node) (rate(container_cpu_usage_seconds_total{{pod=~"{pod_names}"}}[{timespan}])) / on (node) group_left sum by (node) (rate(container_cpu_usage_seconds_total{{job="node-exporter"}}[{timespan}])) * 100'

            #pod_node_cpu_usage = f'sum by (pod, node) (rate(container_cpu_usage_seconds_total{{pod=~"{pod_names}"}}[{timespan}])) / on (node) group_left sum by (node) (rate(container_cpu_usage_seconds_total{{pod=~"{pod_names}"}}[{timespan}])) * 100'            #node_metrics = self.prom_client.query_range(query=node_query, start=self.start_time, end=self.end_time, step=self.step_size)
            pod_node_cpu_usage = f'sum by (pod, node) (rate(container_cpu_usage_seconds_total[{timespan}])) / on (node) group_left sum by (node) (rate(container_cpu_usage_seconds_total[{timespan}])) * 100'           
            #sum by (pod, node) (rate(container_cpu_usage_seconds_total{pod=~"{pod_names}"}[1m])) / on (node) group_left sum by (node) (rate(node_cpu_seconds_total[1m])) * 100
                        
            pod_node_cpu_usage_metrics = self.query_prometheus(self.prometheus_endpoint, pod_node_cpu_usage, interval, timespan)
                            # Process the results

            # Check if the query was successful
            if pod_node_cpu_usage_metrics['status'] == 'success':
                # Get the data from the result
                data = pod_node_cpu_usage_metrics['data']['result']

                # Iterate over each pod in the data
                for pod in data:
                    # Get the pod name and CPU usage
                    if 'pod' not in pod['metric']:
                        pod_name = "non_pod_cpu_usage"
                    else:
                        pod_name = pod['metric']['pod']
                    cpu_usage = pod['value'][1]

                    # Print the pod name and CPU usage
                    print(f'Pod: {pod_name}, CPU Usage: {cpu_usage}')
                    cpu_utilization[pod_name] = float(cpu_usage)
            else:
                # The query was not successful
                print('The query failed')



            # Define the Prometheus query to get the memory usage of pods by node
            #pod_node_memory_usage = f'sum(node_namespace_pod_container:container_memory_working_set_bytes{{pod=~"{pod_names}"}}) by (pod)'

            #pod_node_memory_usage = f'sum by (pod, node) (container_memory_working_set_bytes[{timespan}]) / on (node) group_left sum by (node) (container_memory_working_set_bytes[{timespan}]) * 100'
            pod_node_memory_usage = f'sum by (pod, node) (avg_over_time(container_memory_working_set_bytes[{timespan}])) / on (node) group_left sum by (node) (avg_over_time(container_memory_working_set_bytes[{timespan}])) * 100'


            # Run the query and get the results
            pod_node_memory_usage_metrics = self.query_prometheus(self.prometheus_endpoint, pod_node_memory_usage, interval, timespan)

            # Process the results
            if pod_node_memory_usage_metrics['status'] == 'success':
                # Get the data from the result
                data = pod_node_memory_usage_metrics['data']['result']

                # Iterate over each pod in the data
                for pod in data:
                    # Get the pod name and memory usage
                    if 'pod' not in pod['metric']:
                        pod_name = "non_pod_memory_usage"
                    else:
                        pod_name = pod['metric']['pod']
                    memory_usage = pod['value'][1]

                    # Print the pod name and memory usage
                    print(f'Pod: {pod_name}, Memory Usage: {memory_usage}')
                    if float(memory_usage) < 0:
                        memory_usage = 0
                    memory_utilization[pod_name] = float(memory_usage) 
            else:
                # The query was not successful
                print('The query failed')


            # add observations to dict pod_name : {cpu, memory, gpu}
            for pod in pod_list:
                if pod['name'] in cpu_utilization.keys() : cpu = cpu_utilization[pod['name']]  
                else : cpu = 0
                
                if pod['name'] in memory_utilization.keys(): memory = memory_utilization[pod['name']] 
                else : memory = 0
                observations[pod['name']] = {
                    'node_host_cpu_util_percent': float(cpu),
                    'node_host_memory_util_percent': float(memory),
                    'node_host_gpu_util_percent': 0 #gpu_utilization TODO   
                }

            self.observations = observations
            return self.observations   



        async def calculate(self, carbon_intensity = 100) -> Dict[str, SCIImpactMetricsInterface]:
            pod_list = self.resources
            pod_observations = self.observations

            node_names = [pod['node_name'] for pod in pod_list]

            node_impact_metrics = {}
            for node_name in node_names:
                # create an AKSNode object for each node
                resource_selectors = {
                    "subscription_id": self.resource_selectors.get("subscription_id", None),
                    "resource_group": self.resource_selectors.get("resource_group", None),
                    "cluster_name": self.resource_selectors.get("cluster_name", None),
                    "node_name" : node_name,
                    "prometheus_endpoint": self.resource_selectors.get("prometheus_endpoint", None)
                }
                node = AKSNode(name = node_name, model = self.inner_model,  carbon_intensity_provider=None, auth_object=self.auth_object, resource_selectors=resource_selectors, metadata=self.metadata)
                node_impact_dict = await node.calculate() # get the impact metrics of the node
                #node.fetch_resources()
                #node.fetch_observations()
                node_impact_metrics[node_name] = node_impact_dict
            

            pods_impact = {}
            for pod in pod_list:
                node_name = pod['node_name']
                pod_name = pod['name']
                pod_impact_object = AttributedImpactNodeInterface(name = pod_name,
                                                                    host_node_impact_dict= node_impact_metrics[node_name],
                                                                    carbon_intensity_provider=None,
                                                                    metadata=self.metadata,
                                                                    observations=pod_observations[pod_name],
                                                                    timespan=self.timespan,
                                                                    interval=self.interval)
                res = await pod_impact_object.calculate() # get the impact metrics of the pod
                pods_impact[pod_name] = res[pod_name]  or {} # get the impact metrics of the pod

            return pods_impact