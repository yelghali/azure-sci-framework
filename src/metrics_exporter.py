# sample instanciation with prints of AzureVM class
import sys
import time

import asyncio
import os

#add lib to path
sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.components.azure_aks_node import AKSNode
from lib.components.azure_aks_pod import AKSPod
from lib.components.kubernetes.kubernetes_node import KubernetesNode
from lib.ief.core import *
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.MetricsExporter.exporter import MetricsExporter
from lib.carbonIntensity.kubernetesConfigMapReader import CarbonIntensityKubernetesConfigMap

auth_params = {
}


metadata = {
}


timespan = os.environ.get("TIMESPAN", "PT5M")
interval = os.environ.get("INTERVAL", "PT5M")

KUBELOGIN_AUTH_METHOD = os.environ.get("KUBELOGIN_AUTH_METHOD", "spn")
os.environ["AAD_LOGIN_METHOD"] = KUBELOGIN_AUTH_METHOD

PROMETHEUS_SERVER_ENDPOINT = os.environ.get("PROMETHEUS_SERVER_ENDPOINT", "http://localhost")



subscription_id = os.environ.get("SUBSCRIPTION_ID", "0f4bda7e-1203-4f11-9a85-22653e9af4b4")
resource_group = os.environ.get("AKS_RESOURCE_GROUP", "aks")
cluster_name = os.environ.get("K8S_CLUSTER_NAME", "aks-costdemo")
prometheus_endpoint = os.environ.get("PROMETHEUS_SERVER_ENDPOINT", None)

carbon_intensity_config_map_name = os.environ.get("CARBON_INTENSITY_CONFIG_MAP_NAME", "carbon-intensity")
carbon_intensity_config_map_namespace = os.environ.get("CARBON_INTENSITY_CONFIG_MAP_NAMESPACE", "kube-system")
carbonIntensityProvider_name = os.environ.get("CARBON_INTENSITY_PROVIDER", None)

vm_resource_selectors = {
    "subscription_id": subscription_id,
    #"resource_group": "webapprename",
    #"name": "tototatar",
}


node_resource_selectors = {
    "subscription_id": subscription_id,
     "resource_group": resource_group,
     "cluster_name": cluster_name,
     #"labels" : {"name" : "keda-oper
    #"node_name" : "aks-agentpool-23035252-vmss000005",
     "prometheus_endpoint": prometheus_endpoint
}


pod_resource_selectors = {
    "subscription_id": subscription_id,
     "resource_group": resource_group,
     "cluster_name": cluster_name,
     #"labels" : {"name" : "keda-operator"},
     #"namespace" : "carbon-aware-keda-operator-system",
     #"namespace" : "keda",
     "prometheus_endpoint": prometheus_endpoint
 }


async def process_impact_node(impact_node: ImpactNodeInterface, stop_event: asyncio.Event):
    # fetch the resources and static params once
    await impact_node.fetch_resources()
    await impact_node.lookup_static_params()

    # fetch the observations and calculate + export the impact every 5 minutes
    while not stop_event.is_set():

        # fetch the observations and calculate the impact ; when running calculate, the observations are fetched again        
        impact_metrics = await impact_node.calculate()

        print(impact_metrics)

        # export the metrics to prometheus
        exporter = MetricsExporter(impact_metrics)
        exporter.to_prometheus()
        await asyncio.sleep(300) # wait for 5 minutes before exporting the metrics again


async def main(impact_nodes: List[ImpactNodeInterface]):
    # Create an event to signal the worker when to stop
    stop_event = asyncio.Event()

    # Create the worker tasks
    tasks = []
    for impact_node in impact_nodes:
        task = asyncio.create_task(process_impact_node(impact_node, stop_event))
        tasks.append(task)

    # Wait for the tasks to finish
    await asyncio.gather(*tasks)



params = {
    "namespace": "kube-system",
    "config_map_name": "carbon-intensity",
    "prometheus_server_endpoint": "http://localhost"
}


    

# Program entry point
if __name__ == '__main__':

    if carbonIntensityProvider_name == "CarbonIntensityKubernetesConfigMap":
        print("Using CarbonIntensityKubernetesConfigMap")
        carbonIntensityProvider = CarbonIntensityKubernetesConfigMap(node_resource_selectors)
        carbonIntensityProvider.auth(auth_params)
        carbonIntensityProvider.configure({"namespace": carbon_intensity_config_map_namespace, "config_map_name": carbon_intensity_config_map_name})
    else:
        print("No carbon intensity provider ; using carbon intensity default value : 100 gCO2eq/kWh")
        carbonIntensityProvider = None
    

    #static method
    MetricsExporter.start_http_server(port=8000)

    # 1. Create the impact nodes for which you want to calculate the impact
    # impact_nodes = [
    #     AzureVM(name = "myazurevm", model = ComputeServer_STATIC_IMP(),  
    #          carbon_intensity_provider=carbonIntensityProvider, 
    #          auth_object=auth_params, 
    #          resource_selectors=vm_resource_selectors, 
    #          metadata=metadata,
    #          timespan=timespan,
    #          interval=interval)
    #          , 
    #     AKSNode(name = "myaksclsuter", 
    #             model = ComputeServer_STATIC_IMP(),  
    #             carbon_intensity_provider=carbonIntensityProvider, 
    #             auth_object=auth_params, 
    #             resource_selectors=node_resource_selectors, 
    #             metadata=metadata, 
    #             timespan=timespan, 
    #             interval=interval)
    #         ,
    #     AKSPod(name = "myakspod",
    #             model = ComputeServer_STATIC_IMP(),
    #             carbon_intensity_provider=carbonIntensityProvider,
    #             auth_object=auth_params,
    #             resource_selectors=pod_resource_selectors,
    #             metadata=metadata,
    #             timespan=timespan,
    #             interval=interval)
    #     ]
    
    impact_nodes = [
            KubernetesNode(name = "my-aks-cluster", model = ComputeServer_STATIC_IMP(),  
             carbon_intensity_provider=carbonIntensityProvider, 
             auth_object=auth_params, 
             resource_selectors=node_resource_selectors, 
             metadata=metadata,
             timespan=timespan,
             interval=interval,
             params=params)
    ]
    
    # 2. Run the main function
    asyncio.run(main(impact_nodes))

