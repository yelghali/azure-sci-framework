import requests
from typing import Dict, Any
from lib.components.azure_base import AzureImpactNode
from lib.ief.core import SCIImpactMetricsInterface
from lib.auth.azure import AzureManagedIdentityAuthParams

from kubernetes import client, config
from kubernetes.config.kube_config import KubeConfigLoader

import yaml
import re

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricAggregationType
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential

class AKSNode(AzureImpactNode):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata)
        self.type = "aksnode"
        self.resources = {}
        self.observations = {}
        self.credential = DefaultAzureCredential()
        # Create an instance of AzureManagedIdentityAuthParams to authenticate with Azure using managed identity

    def get_auth_token(self):
        scope = "https://prometheus.monitor.azure.com/.default"
        token = self.credential.get_token(scope)
        return token.token

    
    def list_supported_skus(self):
        return ["Standard_D2_v2"]

    def _get_node_azure_id(self, node):
        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group_name = self.resource_selectors.get("resource_group", None)
        agentpool = node.metadata.labels.get("kubernetes.azure.com/agentpool", None)
        vm_id = 5
        resource_uri = f'subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachineScaleSets/{agentpool}/virtualMachines/{vm_id}'
        return resource_uri


    def fetch_resources(self) -> Dict[str, Any]:
        # Load the Kubernetes configuration from the default location
        config.load_kube_config()

        # Create a Kubernetes API client for the CoreV1Api
        api_client = client.CoreV1Api()

        # Get the name of the current context and cluster from the Kubernetes configuration file
        current_context = config.list_kube_config_contexts()[1]
        current_cluster = current_context['context']['cluster']

        # Query the Kubernetes API server for the list of nodes in the cluster
        if "nodepool_name" in self.resource_selectors:
            nodepool_name = self.resource_selectors["nodepool_name"]
            nodes = api_client.list_node(label_selector=f"nodepool.kubernetes.io/name={nodepool_name}").items
        elif "node_name" in self.resource_selectors:
            node_name = self.resource_selectors["node_name"]
            nodes = api_client.list_node(label_selector=f"kubernetes.io/hostname={node_name}").items
        else:
            nodes = api_client.list_node().items

        # Get the names and metadata of all nodes in the cluster
        node_resources = {}
        for node in nodes:
            node_name = node.metadata.name
            node_resources[node_name] = node

        self.resources = node_resources
        return node_resources

    def fetch_observations(self, aggregation: str = MetricAggregationType.AVERAGE, timespan: str = "PT1H", interval: str = "PT15M") -> Dict[str, Any]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        monitor_client = MonitorManagementClient(self.credential, subscription_id)
        #node_id = self._get_node_id(node_name, resource_group_name)


        observations = {}
        for resource_name, resource  in self.resources.items():
            vm_id = resource.spec.provider_id.replace('azure://','')
            vm_name = resource.metadata.name
            cpu_utilization = None
            memory_utilization = None
            gpu_utilization = None

            # Fetch CPU utilization
            cpu_data = monitor_client.metrics.list(
                resource_uri=vm_id,
                metricnames='Percentage CPU',
                aggregation=aggregation,
                interval=interval,
                timespan=timespan
            )

            # Calculate the average percentage CPU utilization
            total_cpu_utilization = 0
            data_points = 0
            for metric in cpu_data.value:
                for time_series in metric.timeseries:
                    for data in time_series.data:
                        if data.average is not None:
                            total_cpu_utilization += data.average
                            data_points += 1

            average_cpu_utilization = total_cpu_utilization / data_points
            cpu_utilization = average_cpu_utilization
            #print(cpu_utilization)

            # Fetch memory utilization (calculte from available memory since there is no metric for used memory in Azure Monitor)
            memory_data = monitor_client.metrics.list(
                resource_uri=vm_id,
                metricnames='Available Memory Bytes',
                aggregation=aggregation,
                interval=interval,
                timespan=timespan
            )
            
            
            # Calculate the total memory allocated to the virtual machine in bytes
            total_memory_allocated = 1  #GB ; TODO: Fetch from VM SKU


            # Calculate the average available memory in GB
            average_consumed_memory_gb_items =  []
            average_consumed_memory_gb_during_timespan = 0
            for metric in memory_data.value:
                for time_series in metric.timeseries:
                    for data in time_series.data:
                        if data.average is not None:
                            datapoint_average_consumed_memory_gb = total_memory_allocated - (data.average / 1024 ** 3) # /1024 ** 3 converts bytes to GB
                            average_consumed_memory_gb_items.append(datapoint_average_consumed_memory_gb)

            average_consumed_memory_gb_during_timespan = sum(average_consumed_memory_gb_items) / len(average_consumed_memory_gb_items)
            memory_utilization = average_consumed_memory_gb_during_timespan
            print(memory_utilization)
            print(average_consumed_memory_gb_items)
            print(total_memory_allocated)
            # Fetch GPU utilization (if available)
            gpu_utilization = 0 #TODO


            if memory_utilization < 0 : memory_utilization = 0
            self.observations[vm_name] = {
                'average_cpu_percentage': cpu_utilization,
                'average_memory_gb': memory_utilization,
                'average_gpu_percentage': gpu_utilization
            }

        return self.observations   

    def fetch_observations22(self, aggregation: str = MetricAggregationType.AVERAGE, timespan: str = "PT1H", interval: str = "PT15M") -> Dict[str, Any]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group = self.resource_selectors.get("resource_group", None)
        cluster_name = self.resource_selectors.get("cluster_name", None)
        nodepool_name = self.resource_selectors.get("nodepool_name", None)
        prometheus_endpoint = self.resource_selectors.get("prometheus_endpoint", None)

        # Get the list of nodes in the Kubernetes cluster
        #node_info = self.fetch_resources()['nodes']

        nodes = self.fetch_resources()
        node_names = nodes.keys()
        
        # Connect to the Prometheus server
        prometheus_url = "http://prometheus.example.com"
        #prometheus = PrometheusConnect(url=prometheus_url)

        # Define the Prometheus queries to get CPU utilization percentage, total RAM, and GPU utilization percentage by node
        cpu_query = '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle", instance=~"%s"}[5m])) * 100)'
        ram_query = 'sum by (instance) (node_memory_MemTotal_bytes{instance=~"%s"}) / 1024 / 1024'
        gpu_query = 'avg by (instance) (nvidia_gpu_utilization{gpu_name!="", gpu_name!~"MIG.*", instance=~"%s"})'

        # Build the query for all the nodes in the list
        cpu_query_all = cpu_query % '|'.join(node_names)
        ram_query_all = ram_query % '|'.join(node_names)
        gpu_query_all = gpu_query % '|'.join(node_names)

        # Query Prometheus for the CPU utilization percentage, total RAM, and GPU utilization percentage by node
        #cpu_results = prometheus.custom_query_range(query=cpu_query, start="-5m", end="now", step="30s")
        cpu_data = self.query_prometheus(prometheus_endpoint, cpu_query_all, interval, timespan)
        ram_data = self.query_prometheus(prometheus_endpoint, ram_query_all, interval, timespan)
        gpu_data = self.query_prometheus(prometheus_endpoint, gpu_query_all, interval, timespan)

        
        # Check for errors in the Prometheus query results
        if 'status' in cpu_data and cpu_data['status'] == 'error':
            raise Exception(f"Error querying Prometheus for CPU utilization percentage: {cpu_data['error']}")
        if 'status' in ram_data and ram_data['status'] == 'error':
            raise Exception(f"Error querying Prometheus for total RAM: {ram_data['error']}")
        if 'status' in gpu_data and gpu_data['status'] == 'error':
            raise Exception(f"Error querying Prometheus for GPU utilization percentage: {gpu_data['error']}")

        cpu_results = {}
        if cpu_data['status'] == 'success':
            for result in cpu_data['data']['result']:
                if not result['metric']['instance'] :
                    continue
                node_name = result['metric']['instance']
                cpu_results[node_name] = float(result['value'][1])

        mem_results = {}
        if ram_data['status'] == 'success':
            for result in ram_data['data']['result']:
                if not result['metric']['instance'] :
                    continue
                node_name = result['metric']['instance']
                mem_results[node_name] = float(result['value'][1])

        gpu_results = {}
        print(gpu_data)
        if gpu_data['status'] == 'success':
            for result in gpu_data['data']['result']:
                if not result['metric']['instance'] :
                    continue
                node_name = result['metric']['instance']
                gpu_results[node_name] = float(result['value'][1])

        #ram_results = prometheus.custom_query(query=ram_query)
        #gpu_results = prometheus.custom_query_range(query=gpu_query, start="-5m", end="now", step="30s")

        # Store the observations for each node in the dictionary
        observations = {}
        for node_name in node_names:
            observations[node_name] = {
                'cpu_utilization': cpu_results[node_name],
                'ram_total': mem_results[node_name],
                #'gpu_utilization': gpu_results[node_name]
                'gpu_utilization': {} #TODO: fix this
            }
        self.observations = observations
        return observations

    def fetch_observations2(self, aggregation: str = MetricAggregationType.AVERAGE, timespan: str = "PT1H", interval: str = "PT15M") -> Dict[str, Any]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group = self.resource_selectors.get("resource_group", None)
        cluster_name = self.resource_selectors.get("cluster_name", None)
        nodepool_name = self.resource_selectors.get("nodepool_name", None)
        prometheus_endpoint = self.resource_selectors.get("prometheus_endpoint", None)

        # Connect to the Azure Container Service client
        container_service_client = ContainerServiceClient(self.credential, subscription_id)

        # Fetch the AKS cluster
        cluster = container_service_client.managed_clusters.get(resource_group, cluster_name)

        # Fetch the Prometheus endpoint for the AKS cluster
        #prometheus_endpoint = cluster.addon_profiles['omsagent'].config['prometheusEndpoint']


        # Fetch CPU utilization
        cpu_query = '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        cpu_data = self.query_prometheus(prometheus_endpoint, cpu_query, timespan, interval)

        cpu_utilization = {}
        if cpu_data['status'] == 'success':
            for result in cpu_data['data']['result']:
                node_name = result['metric']['instance']
                cpu_utilization[node_name] = float(result['value'][1])

        # Fetch memory utilization
        node_name = "aks-agentpool-59207006-vmss000000"
        memory_query = f'sum by (instance) (container_memory_working_set_bytes)'
        memory_data = self.query_prometheus(prometheus_endpoint, memory_query, timespan, interval)

        # Extract the memory usage value
        memory_utilization = {}
        if memory_data['status'] == 'success':
            print(memory_data)
            for result in memory_data['data']['result']:
                node_name = result['metric']['instance']
                memory_utilization[node_name] = float(result['value'][1])

        # Fetch GPU utilization (if available)
        gpu_query = 'avg(nvidia_gpu_utilization{container_name!="POD",container_name!="",pod_name!=""}) by (pod_name)'
        gpu_data = self.query_prometheus(prometheus_endpoint, gpu_query, timespan, interval)

        gpu_utilization = {}
        if gpu_data['status'] == 'success':
            for result in gpu_data['data']['result']:
                pod_name = result['metric']['instance']
                gpu_utilization[pod_name] = float(result['value'][1])

        self.observations = {
            'percentage_cpu': cpu_utilization,
            'percentage_memory': memory_utilization,
            'percentage_gpu': gpu_utilization
        }

        return self.observations

    def calculate(self, carbon_intensity: float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        return self.inner_model.calculate(self.observations, carbon_intensity=carbon_intensity)

    def lookup_static_params(self) -> Dict[str, Any]:
        return {}

    def query_prometheus(self, prometheus_endpoint: str, query: str, timespan: str, interval: str) -> Dict[str, Any]:
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