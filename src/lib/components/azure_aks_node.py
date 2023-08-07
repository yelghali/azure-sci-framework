import requests
from typing import Dict, Any
from lib.components.azure_base import AzureImpactNode
from lib.ief.core import SCIImpactMetricsInterface
from lib.auth.azure import AzureManagedIdentityAuthParams

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricAggregationType
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential

class AKSNode(AzureImpactNode):
    def __init__(self, model, carbon_intensity_provider, auth_object, resource_selectors, metadata):
        super().__init__(model, carbon_intensity_provider, auth_object, resource_selectors, metadata)
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

    def fetch_resources(self) -> Dict[str, Any]:
        # TODO: Implement fetching of AKS nodes
        pass

    def fetch_observations(self, aggregation: str = MetricAggregationType.AVERAGE, timespan: str = "PT1H", interval: str = "PT15M") -> Dict[str, Any]:
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
                pod_name = result['metric']['pod_name']
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