# sample instanciation with prints of AzureVM class
import sys
from azure.mgmt.monitor.models import MetricAggregationType
import time

import asyncio


#add lib to path
sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.components.azure_aks_node import AKSNode
from lib.components.azure_aks_pod import AKSPod
from lib.components.kubernetes.kubernetes_node import KubernetesNode
from lib.components.kubernetes.kubernetes_pod import KubernetesPod

from lib.ief.core import *
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.MetricsExporter.exporter import MetricsExporter
from lib.carbonIntensity.kubernetesConfigMapReader import CarbonIntensityKubernetesConfigMap

auth_params = {
}

vm_resource_selectors = {
    "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
    #"resource_group": "webapprename",
    #"name": "tototatar",
}

pod_resource_selectors = {
    "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
    "resource_group": "aks",
    "cluster_name": "aks-costdemo",
     #"labels" : {"name" : "keda-operator"},
     #"namespace" : "carbon-aware-keda-operator-system",
     "namespace" : "opencost",
     "prometheus_endpoint": "https://defaultazuremonitorworkspace-neu-b44y.northeurope.prometheus.monitor.azure.com"
 }

node_resource_selectors = {
    "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
    "resource_group": "sus-aks-lab",
    "cluster_name": "sus-aks-lab",
    #"node_name" : "aks-agentpool-23035252-vmss000005",
    "prometheus_endpoint": "https://defaultazuremonitorworkspace-neu-b44y.northeurope.prometheus.monitor.azure.com"
}



node_resource_selectors = {
    "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
    "resource_group": "aks",
    "cluster_name": "aks-costdemo",
    #"node_name" : "aks-agentpool-23035252-vmss000005",
    "prometheus_endpoint": "http://localhost"
}


metadata = {

}

timespan = "PT1H"
interval = "PT5M"



vm = AzureVM(name = "mywebserver", model = ComputeServer_STATIC_IMP(),  
             carbon_intensity_provider=None, 
             auth_object=auth_params, 
             resource_selectors=vm_resource_selectors, 
             metadata=metadata,
             timespan=timespan,
             interval=interval)


# manual_observations = {
#      "node_host_cpu_util_percent" : 50,
#      "node_host_memory_util_percent" : 50,
#      "node_host_gpu_util_percent" : 50
#  }

# workload = AttributedImpactNodeInterface(name = "myworkload", 
#                                           host_node=vm, 
#                                           carbon_intensity_provider=None, 
#                                           metadata=metadata, 
#                                           observations=manual_observations,
#                                           timespan=timespan,
#                                           interval=interval)
# #print(workload.calculate())




# aggregation = MetricAggregationType.AVERAGE

#print(node)
# node.fetch_resources()
# print(node.lookup_static_params())
# print(node.fetch_observations())
# print(node.calculate())

# #print(node.fetch_observations(interval="PT15M", timespan="PT1H"))

# print(node.calculate())

import os

KUBELOGIN_AUTH_METHOD = os.environ.get("KUBELOGIN_AUTH_METHOD", "spn")
os.environ["AAD_LOGIN_METHOD"] = KUBELOGIN_AUTH_METHOD

PROMETHEUS_SERVER_ENDPOINT = os.environ.get("PROMETHEUS_SERVER_ENDPOINT", "http://localhost")


async def main1():


    # carbonIntensityProvider = CarbonIntensityKubernetesConfigMap(node_resource_selectors)
    # carbonIntensityProvider.auth(auth_params)
    # carbonIntensityProvider.configure({"namespace": "kube-system", "config_map_name": "carbon-intensity"})
 
    # node = AKSNode(name = "myaksclsuter", model = ComputeServer_STATIC_IMP(),  carbon_intensity_provider=None, auth_object=auth_params, resource_selectors=node_resource_selectors, metadata=metadata, timespan=timespan, interval=interval)
    # uuu = await node.calculate()
    # print(uuu)


    params = {
        "namespace": "kube-system",
        "config_map_name": "carbon-intensity",
        "prometheus_server_endpoint": PROMETHEUS_SERVER_ENDPOINT
                }

    k8snode = KubernetesNode(name = "my-aks-cluster", model = ComputeServer_STATIC_IMP(),  
             carbon_intensity_provider=None, 
             auth_object=auth_params, 
             resource_selectors=node_resource_selectors, 
             metadata=metadata,
             timespan=timespan,
             interval=interval,
             params=params)

    pod = KubernetesPod(name = "myakspod", 
                        model = ComputeServer_STATIC_IMP(),  
                        carbon_intensity_provider=None, 
                        auth_object=auth_params, 
                        resource_selectors=pod_resource_selectors, 
                        metadata=metadata,
                        timespan=timespan,
                        interval=interval,
                        params=params)


    while(True):
        #toto = await k8snode.calculate()
        #toto = await k8snode.fetch_observations()
        toto = await pod.calculate()
        print(toto)
        time.sleep(300)


    # toto = await vm.fetch_resources()
    # print(toto)
    # tata = await vm.lookup_static_params()
    # print(tata)


    # #tutu = await vm.fetch_observations()
    # #print(tutu)
    # uuu = await vm.calculate()
    # print(uuu)


    # await node.fetch_resources()
    # toto = await node.lookup_static_params()
    # print(toto)
    # tutu = await node.fetch_observations()
    # print(tutu)
    #uuu = await node.calculate()
    #print(uuu)



    #toto = await pod.fetch_resources()
    toto = await pod.lookup_static_params()
    #print(toto)
    # #await pod.fetch_observations()
    # ttoto = await pod.calculate()
    # #print(ttoto)

if __name__ == '__main__':
    asyncio.run(main1())

# async def process_impact_node(impact_node: ImpactNodeInterface, stop_event: asyncio.Event):
#     # fetch the resources and static params once
#     await impact_node.fetch_resources()
#     await impact_node.lookup_static_params()

#     # fetch the observations and calculate + export the impact every 5 minutes
#     while not stop_event.is_set():

#         # fetch the observations and calculate the impact ; when running calculate, the observations are fetched again        
#         impact_metrics = await impact_node.calculate()

#         print(impact_metrics)

#         # export the metrics to prometheus
#         exporter = MetricsExporter(impact_metrics)
#         exporter.to_prometheus()
#         await asyncio.sleep(300) # wait for 5 minutes before exporting the metrics again


# async def main(impact_nodes: List[ImpactNodeInterface]):
#     # Create an event to signal the worker when to stop
#     stop_event = asyncio.Event()

#     # Create the worker tasks
#     tasks = []
#     for impact_node in impact_nodes:
#         task = asyncio.create_task(process_impact_node(impact_node, stop_event))
#         tasks.append(task)

#     # Wait for the tasks to finish
#     await asyncio.gather(*tasks)


# # Program entry point
# if __name__ == '__main__':

#     carbonIntensityProvider = CarbonIntensityKubernetesConfigMap(node_resource_selectors)
#     carbonIntensityProvider.auth(auth_params)
#     carbonIntensityProvider.configure({"namespace": "kube-system", "config_map_name": "carbon-intensity"})
 

#     #static method
#     MetricsExporter.start_http_server(port=8000)

#     # 1. Create the impact nodes for which you want to calculate the impact
#     impact_nodes = [
#         AzureVM(name = "myazurevm", model = ComputeServer_STATIC_IMP(),  
#              carbon_intensity_provider=carbonIntensityProvider, 
#              auth_object=auth_params, 
#              resource_selectors=vm_resource_selectors, 
#              metadata=metadata,
#              timespan=timespan,
#              interval=interval)
#              , 
#         AKSNode(name = "myaksclsuter", 
#                 model = ComputeServer_STATIC_IMP(),  
#                 carbon_intensity_provider=carbonIntensityProvider, 
#                 auth_object=auth_params, 
#                 resource_selectors=node_resource_selectors, 
#                 metadata=metadata, 
#                 timespan=timespan, 
#                 interval=interval)
#             ,
#         AKSPod(name = "myakspod",
#                 model = ComputeServer_STATIC_IMP(),
#                 carbon_intensity_provider=carbonIntensityProvider,
#                 auth_object=auth_params,
#                 resource_selectors=pod_resource_selectors,
#                 metadata=metadata,
#                 timespan=timespan,
#                 interval=interval)
#         ]
    
#     # 2. Run the main function
#     asyncio.run(main(impact_nodes))






#print(vm.fetch_resources())
#print(vm.lookup_static_params())
#print(vm.fetch_observations())

#print(vm.calculate())
#print(node.fetch_resources())



#static method
# MetricsExporter.start_http_server(port=8000)
# while(True):

#     print(vm.fetch_observations())
#     #print(vm.observations)
#     data = vm.calculate()

    
#     exporter = MetricsExporter(data)
#     #exporter.to_csv('metrics.csv')
#     #exporter.to_json('metrics.json')
#     exporter.to_prometheus()

#     print(node.fetch_observations())
#     data = node.calculate()
#     exporter = MetricsExporter(data)
#     exporter.to_prometheus()



#     # pod.fetch_observations()
#     # data = pod.calculate()
#     # exporter = MetricsExporter(data)
#     # exporter.to_prometheus()

#     #sleep 5 mins 
#     time.sleep(300)


