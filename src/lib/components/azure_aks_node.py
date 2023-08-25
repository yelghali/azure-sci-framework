import requests
from typing import Dict, Any
from lib.components.azure_vm import AzureVM
from lib.ief.core import SCIImpactMetricsInterface
from lib.auth.azure import AzureManagedIdentityAuthParams

from kubernetes import client, config
from kubernetes.config.kube_config import KubeConfigLoader

import yaml
import re
import csv
import os
import io

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricAggregationType
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential


import asyncio
import itertools

aggregation = MetricAggregationType.AVERAGE #for monitoring queries

semaphore_max = 5 # to avoid throttling ; this is the max number of concurrent queries for Azure Monitor

class AKSNode(AzureVM):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval="PT5M", timespan="PT1H"):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval, timespan)
        self.type = "azure.compute.aks.node"
        self.resources = {}
        self.observations = {}
        self.credential = DefaultAzureCredential()
        self.static_params = {}
        # Create an instance of AzureManagedIdentityAuthParams to authenticate with Azure using managed identity

    def get_auth_token(self):
        scope = "https://prometheus.monitor.azure.com/.default"
        token = self.credential.get_token(scope)
        return token.token

    
    def list_supported_skus(self):
        return ["Standard_D2_v2"]

    # def _get_node_azure_id(self, node):
    #     subscription_id = self.resource_selectors.get("subscription_id", None)
    #     resource_group_name = self.resource_selectors.get("resource_group", None)
    #     agentpool = node.metadata.labels.get("kubernetes.azure.com/agentpool", None)
    #     vm_id = 5
    #     resource_uri = f'subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachineScaleSets/{agentpool}/virtualMachines/{vm_id}'
    #     return resource_uri


    async def fetch_resources(self) -> Dict[str, object]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group_name = self.resource_selectors.get("resource_group", None)
        cluster_name = self.resource_selectors.get("cluster_name", None)
        container_service_client = ContainerServiceClient(self.credential, subscription_id)
        
        kubeconfig = container_service_client.managed_clusters.list_cluster_user_credentials(resource_group_name, cluster_name).kubeconfigs[0].value

        kubeconfig_stream = io.BytesIO(kubeconfig)
        kubeconfig_dict = yaml.safe_load(kubeconfig_stream)
        

        # Get the name of the current context and cluster from the kubeconfig dict
        #current_context = kubeconfig_dict["current-context"]
        #current_cluster = kubeconfig_dict["contexts"][0]["context"]["cluster"]


        # Load the Kubernetes configuration from the kubeconfig
        loader = KubeConfigLoader(config_dict=kubeconfig_dict)
        configuration = client.Configuration()
        loader.load_and_set(configuration)
        client.Configuration.set_default(configuration)

        # Create a Kubernetes API client for the CoreV1Api
        api_client = client.CoreV1Api()


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


    async def fetch_gpu_utilization(self, resource: object, monitor_client: MonitorManagementClient) -> float:
        return 0 #TODO


    async def fetch_observations(self) -> Dict[str, object]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        monitor_client = MonitorManagementClient(self.credential, subscription_id)
        #node_id = self._get_node_id(node_name, resource_group_name)

        if self.resources == {} or self.resources == None: await self.fetch_resources()
        if self.static_params == {} or self.static_params == None: await self.lookup_static_params()

        # Create a semaphore with an initial value of 3
        semaphore = asyncio.Semaphore(semaphore_max) # to avoid throttling ; this is the max number of concurrent queries for Azure Monitor



        cpu_memory_tasks = []
        gpu_tasks = []
        for resource_name, resource in self.resources.items():
            if hasattr(resource.spec, 'provider_id'):
                vm_id = resource.spec.provider_id.replace('azure://','')
                vm_name = resource.metadata.name
                instance_memory = self.static_params[resource_name]['instance_memory']

                cpu_memory_tasks.append(asyncio.create_task(self.fetch_cpu_memory_utilization(semaphore, vm_id, instance_memory, monitor_client)))
                gpu_tasks.append(asyncio.create_task(self.fetch_gpu_utilization(resource, monitor_client)))

        cpu_memory_results = await asyncio.gather(*cpu_memory_tasks)
        gpu_results = await asyncio.gather(*gpu_tasks)

        for i, (resource_name, resource) in enumerate(self.resources.items()):
            if hasattr(resource.spec, 'provider_id'):
                vm_name = resource.metadata.name
                cpu_utilization, memory_utilization = cpu_memory_results[i]
                gpu_utilization = gpu_results[i] #returns 0 for now ; TOOD

                self.observations[vm_name] = {
                    'average_cpu_percentage': cpu_utilization,
                    'average_memory_gb': memory_utilization,
                    'average_gpu_percentage': gpu_utilization
                }

        return self.observations

 

    async def calculate(self, carbon_intensity: float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        # if self.resources == {}: call fetch_resources
        if self.resources == {} or self.resources == None:
            await self.fetch_resources()
        # if self.static_params == {}: call lookup_static_params
        if self.static_params == {} or self.static_params == None:
            await self.lookup_static_params()

        #always get updated observations
        await self.fetch_observations()

        return self.inner_model.calculate(self.observations, carbon_intensity=carbon_intensity, interval=self.interval, timespan=self.timespan, metadata=self.metadata, static_params=self.static_params)


    async def lookup_static_params(self) -> Dict[str, object]:

        if self.resources == {} or self.resources == None: await self.fetch_resources()

        # Create a list of coroutines to run concurrently using a list comprehension
        coroutines = [
            (
                self.get_vm_sku_tdp(resource.metadata.labels.get("beta.kubernetes.io/instance-type", "")),
                self.get_vm_resources(resource.metadata.labels.get("beta.kubernetes.io/instance-type", "")),
                self.get_vm_te(resource.metadata.labels.get("beta.kubernetes.io/instance-type", ""))
            )
            for resource_name, resource in self.resources.items()
        ]

        # Run the coroutines concurrently using asyncio.gather
        results = await asyncio.gather(*[coro for coro in itertools.chain(*coroutines)])

        # Process the results and update the static_params dictionary
        i = 0
        for resource_name, resource in self.resources.items():
            vm_name = resource.metadata.name
            vm_sku_tdp = results[i]
            rr, total_vcpus, instance_memory = results[i+1]
            te = results[i+2]

            self.static_params[vm_name] = {
                'vm_sku': resource.metadata.labels.get("beta.kubernetes.io/instance-type", ""),
                'vm_sku_tdp': vm_sku_tdp,
                'rr': rr,
                'total_vcpus': total_vcpus,
                'te': te,
                'instance_memory': instance_memory
            }

            i += 3

        return self.static_params


    # def lookup_static_params1(self) -> Dict[str, object]:

    #     for resource_name, resource  in self.resources.items():
    #         vm_id = resource.spec.provider_id.replace('azure://','')
    #         vm_name = resource.metadata.name

    #         vm_sku = resource.metadata.labels.get("beta.kubernetes.io/instance-type", "")
    #         agent_pool = resource.metadata.labels.get("agentpool", "")

    #         vm_sku_tdp = self.get_vm_sku_tdp(vm_sku)
    #         rr, total_vcpus, instance_memory = self.get_vm_resources(vm_sku)
    #         te = self.get_vm_te(vm_sku)

    #         self.static_params[vm_name] = {
    #             'vm_sku': vm_sku,
    #             'vm_sku_tdp': vm_sku_tdp,
    #             'rr': rr,
    #             'total_vcpus': total_vcpus,
    #             'te': te,
    #             'instance_memory': instance_memory
    #         }
    #     return self.static_params


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