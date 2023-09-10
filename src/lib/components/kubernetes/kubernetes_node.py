import requests
from typing import Dict, Any, Tuple
from lib.ief.core import *

from kubernetes import client, config
from kubernetes.config.kube_config import KubeConfigLoader

import itertools
import asyncio
import yaml
import re
import csv
import os
import io
import subprocess
import json

from azure.identity import ClientSecretCredential

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricAggregationType
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential


OPENCOST_API_URL = os.environ.get("OPENCOST_API_URL", "http://opencost.opencost.svc:9003").rstrip("/")
OPENCOST_API_URL = os.environ.get("OPENCOST_API_URL", "http://localhost:9003").rstrip("/")


class KubernetesNode(ImpactNodeInterface):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval="PT5M", timespan="PT1H", params={}):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval, timespan, params)
        self.type = "kubernetes.node"
        self.resources = {}
        self.observations = {}
        self.credential = None
        self.static_params = {}
        self.properties = {}
        self.prometheus_url = params.get("prometheus_server_endpoint", None)
        self.credential = DefaultAzureCredential()

    #     self.validate_configuration()

    # def validate_configuration(self):
    #     if not self.prometheus_url:
    #         raise Exception("Prometheus server endpoint not provided, in params {}")
    
    def list_supported_skus(self):
        return []

    # def _get_node_azure_id(self, node):
    #     subscription_id = self.resource_selectors.get("subscription_id", None)
    #     resource_group_name = self.resource_selectors.get("resource_group", None)
    #     agentpool = node.metadata.labels.get("kubernetes.azure.com/agentpool", None)
    #     vm_id = 5
    #     resource_uri = f'subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachineScaleSets/{agentpool}/virtualMachines/{vm_id}'
    #     return resource_uri


    async def azure_authenticate(self, auth_params: Dict[str, object] = {}) -> None:
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
        print("Kubernetes azure auth configuration set successfully.")


    async def kubelogin_azure_authenticate(self):

        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group_name = self.resource_selectors.get("resource_group", None)
        cluster_name = self.resource_selectors.get("cluster_name", None)
        # Authenticate with Azure and get the kubeconfig for the cluster

        
        TENANT_ID = os.environ.get("AZURE_TENANT_ID", None)
        CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", None)
        CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", None)
        #check that the credentials are not None, otherwise use the default credential and send a warning message
        try:
            print("using default Azure credential")
            credential = DefaultAzureCredential()
        except Exception as e:
            print(f"Error loading DefaultAzureCredential: {e}")
            print("using service principal credential")
            credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)

        container_service_client = ContainerServiceClient(credential, subscription_id)

        kubeconfig = container_service_client.managed_clusters.list_cluster_user_credentials(resource_group_name, cluster_name).kubeconfigs[0].value

        # Load the kubeconfig into a dictionary
        kubeconfig_stream = io.BytesIO(kubeconfig)
        kubeconfig_dict = yaml.safe_load(kubeconfig_stream)


        # Load the Kubernetes configuration from the updated kubeconfig
        loader = KubeConfigLoader(config_dict=kubeconfig_dict)
        configuration = client.Configuration()
        loader.load_and_set(configuration)
        client.Configuration.set_default(configuration)
        
        # Update the kubeconfig to use the service principal for authentication
        #subprocess.run(["kubelogin", "convert-kubeconfig", "-l", "spn", "--client-id", spn_client_id, "--client-secret", spn_client_secret])
        subprocess.run(["kubelogin", "convert-kubeconfig", "-l", "spn"])

        print("authentication successful using kubelogin_azure_authenticate")


    async def kub_authenticate(self, auth_params: Dict[str, object] = {}) -> None:
        # Load the Kubernetes configuration from the default location
        try:
            config.load_kube_config()
        except Exception as e:
            raise Exception(f"Error loading Kubernetes configuration: {e}")
        print("Kubernetes configuration loaded successfully.")

    async def authenticate(self, auth_params: Dict[str, object] = {}) -> None:
        try:
            await self.kub_authenticate()
        except Exception as e:
            print(f"Error authenticating to Kubernetes cluster: {e}")
            print("Trying to authenticate to Azure instead...")
            try:    
                await self.kubelogin_azure_authenticate()
            except Exception as e:
                raise Exception(f"Error authenticating to Azure cluster: {e}")
        print("Kubernetes authentication successful.")

    async def fetch_resources(self) -> Dict[str, Any]:
        await self.authenticate()
        
        # Create a Kubernetes API client for the CoreV1Api
        api_client = client.CoreV1Api()

        # Create a Kubernetes API client for the CoreV1Api
        #api_client = client.CoreV1Api()

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
    

    async def get_resource_properties(self) -> Dict[str, Any]:
        if not self.resources or self.resources == {}:
            await self.fetch_resources()

        node_resources = self.resources
        node_properties = {}
        for node_name, node in node_resources.items():
            node_properties[node_name] = {
            #id is cluster/agentpool/node
            "id": f"{node.metadata.labels['kubernetes.azure.com/cluster']}/{node.metadata.labels['agentpool']}/{node_name}",
            "cluster": node.metadata.labels.get('kubernetes.azure.com/cluster', ''),
            "node": node_name,
            "agentpool": node.metadata.labels.get('agentpool', ''),
            "sku" : node.metadata.labels.get('beta.kubernetes.io/instance-type', ''),
            "region" : node.metadata.labels.get('topology.kubernetes.io/region', ''),
            "zone" : node.metadata.labels.get('topology.kubernetes.io/zone', ''),
            "os-sku": node.metadata.labels.get('kubernetes.azure.com/os-sku', ''),
            "arch": node.status.node_info.architecture,
            "providerID": node.spec.provider_id,
            "labels": node.metadata.labels,
            "cpu_cores": node.status.capacity.get('cpu', 0),
            "memory_bytes": node.status.capacity.get('memory', 0),
            "gpu_count": node.status.capacity.get('nvidia.com/gpu', 0),
            "cpu_allocatable": node.status.allocatable.get('cpu', 0),
            "memory_allocatable": node.status.allocatable.get('memory', 0),
            "gpu_allocatable": node.status.allocatable.get('nvidia.com/gpu', 0)
            
        }
        
        self.resource_properties = node_properties
        return node_properties


    #fetch CPU, RAM & GPU usage metrics from opencost API
    async def fetch_observations(self) -> Dict[str, object]:
        if not self.resources or self.resources == {}:
            await self.fetch_resources()

        
        timespan = self.timespan.lower().replace("pt", "")
        interval = self.interval.lower().replace("pt", "")

        url = "%s/allocation/compute?window=%s&resolution=%s&aggregate=node" % (OPENCOST_API_URL, timespan, interval)
        print("fetching CPU, RAM, GPU usage from opencost API : %s" % url)

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()["data"][0]
            observations = {}
            for node_name, item in data.items():
                if node_name in self.resources.keys():
                    cpu_util = float(item["cpuCoreUsageAverage"]) 
                    memory_gb = float(item["ramBytes"] / (1024 ** 3))

                    observations[node_name] = {
                    #     "average_cpu_percentage": cpu_util, 
                    #   "average_memory_gb": avg_memory_gb,
                    #     "average_gpu_percentage" : 0 #TODO: add gpu
                                "average_cpu_percentage": cpu_util, 
                                "cpuCoreHours" : float(item["cpuCoreHours"]),
                                "tr" : float(item["cpuCoreHours"]),
                                "cpuCores" : float(item["cpuCores"]),
                                "rr" : float(item["cpuCores"]),
                                "memory_gb": memory_gb,
                                "ramByteHours" : float(item["ramByteHours"]),
                                "ramBytes" : float(item["ramBytes"]),
                                "average_gpu_percentage" : 0, #gpu_utilization TODO
                                "gpuCount" : float(item["gpuCount"]),
                                "gpuHours" : float(item["gpuHours"])
                      }
            self.observations = observations
            return observations
        else:
            raise Exception(f"Error fetching observations from {url}: {response.status_code} {response.text}")

    # async def fetch_observations2(self) -> Dict[str, object]:
    #     if not self.resources or self.resources == {}:
    #         await self.fetch_resources()

    #     timespan = self.timespan.lower().replace("pt", "")
    #     interval = self.interval.lower().replace("pt", "")
 
    #     cpu_query = f'(100 - avg by (node) (irate(node_cpu_seconds_total{{mode="idle"}}[{interval}]))) * 100'
    #     memory_query = f'avg by (node) ((node_memory_MemTotal_bytes - node_memory_MemFree_bytes - node_memory_Buffers_bytes - node_memory_Cached_bytes) / 1024 / 1024 / 1024)'

    #     cpu_data = await self.query_prometheus(cpu_query, interval=interval)
    #     memory_data = await self.query_prometheus(memory_query, interval=interval)


    #     observations = {}
    #     for node_name, node in self.resources.items():
    #         cpu_percentage = None
    #         memory_GB = None

    #         for cpu_result in cpu_data:
    #             if cpu_result['metric']['node'] == node_name:
    #                 cpu_percentage = float(cpu_result['value'][1])
    #                 break

    #         for memory_result in memory_data:
    #             if memory_result['metric']['node'] == node_name:
    #                 memory_GB = float(memory_result['value'][1])
    #                 break

    #         observations[node_name] = {
    #             'average_cpu_percentage': cpu_percentage,
    #             'average_memory_gb': memory_GB,
    #             'average_gpu_percentage' : 0 #TODO: add gpu

    #         }

    #     self.observations = observations
    #     return observations


    async def calculate(self, carbon_intensity: float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        # if self.resources == {}: call fetch_resources
        if self.resources == {} or self.resources == None:
            await self.fetch_resources()
        # if self.static_params == {}: call lookup_static_params
        if self.static_params == {} or self.static_params == None:
            await self.lookup_static_params()

        #always get updated observations
        await self.fetch_observations()

        return await self.inner_model.calculate(self.observations, carbon_intensity=self.carbon_intensity_provider, interval=self.interval, timespan=self.timespan, metadata=self.metadata, static_params=self.static_params)


    async def query_prometheus(self, query: str, timestamp : str = '1h', interval : str = '5m') -> Dict[str, object]:
        response = requests.get(f'{self.prometheus_url}/api/v1/query', params={'query': query, 'step' : interval})
        print(query)
        return response.json()['data']['result']
    

    
    async def get_vm_sku_tdp(self, vm_sku: str) -> int:
        # Get TDP for the VM sku, from the static data file
        vm_sku_tdp = 180  # default value for unknown VM SKUs
        with open('lib/static_data/azure_vm_tdp.csv', 'r') as f:
            for line in f:
                if vm_sku in line:
                    vm_sku_tdp = line.split(',')[1]
                    break
        return vm_sku_tdp


    async def get_vm_resources(self, vm_sku: str) -> Tuple[int, float, float]:
        # Get RR, TR and instance memory for the VM sku, from the static data file
        rr = 2  # vCPUs
        total_vcpus = 16
        instance_memory = 0.0
        with open('lib/static_data/ccf_azure_instances.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            vm_sku_short = ''.join(vm_sku.split('_')[1:])
            for row in reader:
                if row['Virtual Machine'].replace(" ", "").lower() == vm_sku_short.replace(" ", "").lower():
                    rr = int(row['Instance vCPUs'])
                    total_vcpus = float(row['Platform vCPUs (highest vCPU possible)'])
                    instance_memory = float(row['Instance Memory'])
                    break
        return rr, total_vcpus, instance_memory


    async def get_vm_te(self, vm_sku: str) -> float:
        # Get TE for the VM sku, from the static data file
        te = 1200
        with open('lib/static_data/ccf_coefficients-azure-embodied.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            vm_sku_short = vm_sku.split('_')[1]
            for row in reader:
                if row['type'].replace(" ", "").lower() == vm_sku_short.replace(" ", "").lower():
                    te = float(row['total'])
                    break
        return te



    async def lookup_static_params(self) -> Dict[str, object]:

        if self.resources == {} or self.resources == None: 
            await self.fetch_resources()
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
            instance_vcpus, platform_total_vcpus, instance_memory = results[i+1]
            te = results[i+2]

            self.static_params[vm_name] = {
                'vm_sku': resource.metadata.labels.get("beta.kubernetes.io/instance-type", ""),
                'vm_sku_tdp': vm_sku_tdp,
                'instance_vcpus': instance_vcpus,
                'total_vcpus': platform_total_vcpus,
                'te': te,
                'instance_memory': instance_memory
            }

            i += 3

        return self.static_params
