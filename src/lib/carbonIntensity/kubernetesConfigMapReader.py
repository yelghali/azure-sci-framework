import requests
from typing import Dict, Any
from lib.ief.core import *

from kubernetes import client, config
from kubernetes.config.kube_config import KubeConfigLoader

import yaml
import re
import csv
import os
import io
import base64
import json
from datetime import datetime

from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential


class CarbonIntensityKubernetesConfigMap(CarbonIntensityPluginInterface):
    def __init__(self, resource_selectors: Dict[str, Any]):
        self.api_client = None
        self.namespace = None
        self.config_map_name = None
        self.credential = DefaultAzureCredential()
        self.resource_selectors = resource_selectors


    def auth(self, auth_params: Dict[str, object]) -> None:
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

    def configure(self, params: Dict[str, object]) -> None:
        # Get the namespace and ConfigMap name from the configuration parameters
        self.namespace = params.get('namespace', 'kube-system')
        self.config_map_name = params.get('config_map_name', 'carbon-intensity')

        # Create Kubernetes API client
        self.api_client = client.CoreV1Api()

    async def get_current_carbon_intensity(self) -> float:
        # Get the carbon-intensity ConfigMap from the namespace
        config_map = self.api_client.read_namespaced_config_map(self.config_map_name, self.namespace)

        # Decode the binary data
        data = base64.b64decode(config_map.binary_data['data'])

        # Parse the JSON data
        forecasts = json.loads(data)

        # Find the forecast closest to the current time
        now = datetime.utcnow()
        closest_forecast = None
        closest_delta = None
        for forecast in forecasts:
            forecast_time = datetime.strptime(forecast['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            delta = abs(now - forecast_time)
            if closest_delta is None or delta < closest_delta:
                closest_forecast = forecast
                closest_delta = delta

        # Return the current carbon intensity value
        print("current time: %s" % now)
        print("closest forecast: %s" % closest_forecast)
        return closest_forecast