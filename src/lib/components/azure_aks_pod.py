import requests
from typing import Dict, Any
from lib.components.azure_base import AzureImpactNode
from lib.components.azure_aks_node import AKSNode
from lib.ief.core import *
from lib.auth.azure import AzureManagedIdentityAuthParams

from kubernetes import client, config
from kubernetes.config.kube_config import KubeConfigLoader

import yaml
import re

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricAggregationType
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential

class AKSPod(AttributedImpactNodeInterface):
        def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata):
            super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata)
            self.type = "akspod"
            self.resources = {}
            self.observations = {}
            self.credential = DefaultAzureCredential()
            self.resource_selectors = resource_selectors

        def fetch_resources(self) -> Dict[str, Any]:
            config.load_kube_config()
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

            for item in pods:
                pod = {}
                pod['name'] = item.metadata.name
                pod['namespace'] = item.metadata.namespace
                pod['labels'] = item.metadata.labels
                pod['node_name'] = item.spec.node_name
                pod_list.append(pod)
            
            self.resources = pod_list
            return self.resources