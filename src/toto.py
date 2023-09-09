import json
import subprocess
from kubernetes import client, config
from kubernetes.config.kube_config import Configuration

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


os.environ["AAD_LOGIN_METHOD"] = "spn"

def list_nodes2(cluster_name: str, region: str):
    # Obtain the AKS token using kubelogin
    server_id = "6dae42f8-4368-4678-94ff-3960e28e3630"
    tenant_id = "16b3c013-d300-468d-ac64-7eda0820b6d3"
    client_id ="0794bb09-72b3-4811-a6a9-6455a3a3e1a3"
    client_secret = "RLf8Q~WSTWQKqOkRfGgDbd5MmseWcGxdKr~1OcWi"
    cmd = ["kubelogin", "get-token", "--server-id", server_id, "--tenant-id", tenant_id, "--client-id", client_id, "--client-secret", client_secret, "--login", "spn"]
    
    output = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(output)
    output_dict = json.loads(output.stdout)
    token = output_dict["status"]["token"]

    # Set the API key for the cluster
    configuration = Configuration()
    configuration.host = f"https://sus-aks-lab-dns-fpt9ebbr.hcp.francecentral.azmk8s.io:443"
    #configuration.verify_ssl = False
    configuration.api_key = {
        "authorization": f"Bearer {token}"
    }

    # Create an API client instance with the configuration
    api_client = client.ApiClient(configuration)

    # Create an instance of the CoreV1Api
    v1 = client.CoreV1Api(api_client)

    # List the nodes in the cluster
    nodes = v1.list_node()

    # Print the node names
    for node in nodes.items:
        print(node.metadata.name)


#list_nodes("aks-costdemo", "francecentral")


def list_nodes():
    credential = DefaultAzureCredential()
    subscription_id = "0f4bda7e-1203-4f11-9a85-22653e9af4b4"
    resource_group_name =  "aks"
    cluster_name = "aks-costdemo"
    container_service_client = ContainerServiceClient(credential, subscription_id)



    print("Getting cluster access credentials...")
    kubeconfig = container_service_client.managed_clusters.list_cluster_user_credentials(resource_group_name, cluster_name).kubeconfigs[0].value

    print("Decoding kubeconfig...")
    kubeconfig_stream = io.BytesIO(kubeconfig)
    kubeconfig_dict = yaml.safe_load(kubeconfig_stream)

    kubeconfig_file = os.path.expanduser("~/.kube/config")  # or "%USERPROFILE%\.kube\config" on Windows
    with open(kubeconfig_file, "w") as f:
        yaml.dump(kubeconfig_dict, f)

    print(kubeconfig_dict)



    server_id = "6dae42f8-4368-4678-94ff-3960e28e3630"
    tenant_id = "16b3c013-d300-468d-ac64-7eda0820b6d3"
    client_id ="0794bb09-72b3-4811-a6a9-6455a3a3e1a3"
    client_secret = "RLf8Q~WSTWQKqOkRfGgDbd5MmseWcGxdKr~1OcWi"
    cmd = ["kubelogin", "get-token", "--server-id", server_id, "--tenant-id", tenant_id, "--client-id", client_id, "--client-secret", client_secret, "--login", "spn"]
    
    output = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(output)
    #output_dict = json.loads(output.stdout)
    #token = output_dict["status"]["token"]



    # Get the name of the current context and cluster from the kubeconfig dict
    #current_context = kubeconfig_dict["current-context"]
    #current_cluster = kubeconfig_dict["contexts"][0]["context"]["cluster"]


    print("Loading kubeconfig...")
    # Load the Kubernetes configuration from the kubeconfig
    #loader = KubeConfigLoader(config_dict=kubeconfig_dict)
    #configuration = client.Configuration()
    #loader.load_and_set(configuration)
    #client.Configuration.set_default(configuration)

    config.load_kube_config()
    # Create a Kubernetes API client for the CoreV1Api
    api_client = client.CoreV1Api()



list_nodes()