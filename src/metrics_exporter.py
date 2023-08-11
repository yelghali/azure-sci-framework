# sample instanciation with prints of AzureVM class
import sys
from azure.mgmt.monitor.models import MetricAggregationType
import time

sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.components.azure_aks_node import AKSNode
from lib.components.azure_aks_pod import AKSPod
from lib.ief.core import *
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.MetricsExporter.exporter import MetricsExporter

auth_params = {
    "tenant_id": "12345678-1234-1234-1234-123456789012",
    "client_id": "12345678-1234-1234-1234-123456789012",
    "client_secret": "12345678-1234-1234-1234-123456789012"
}

resource_selectors = {
    "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
    "resource_group": "webapprename",
    "name": "tototatar",
}

metadata = {
    "region": "westeurope"
}

timespan = "PT24H"
interval = "PT5M"

vm = AzureVM(name = "mywebserver", model = ComputeServer_STATIC_IMP(),  
             carbon_intensity_provider=None, 
             auth_object=auth_params, 
             resource_selectors=resource_selectors, 
             metadata=metadata,
             timespan=timespan,
             interval=interval)

print(vm.fetch_resources())
print(vm.fetch_observations())
print(vm.calculate())

# manual_observations = {
#     "node_host_cpu_util_percent" : 50,
#     "node_host_memory_util_percent" : 50,
#     "node_host_gpu_util_percent" : 50,
# }

# workload = AttributedImpactNodeInterface(name = "myworkload", 
#                                          host_node=vm, 
#                                          carbon_intensity_provider=None, 
#                                          metadata=metadata, 
#                                          observations=manual_observations)
#print(workload.calculate())



# resource_selectors = {
#     "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
#     "resource_group": "sus-aks-lab",
#     "cluster_name": "sus-aks-lab",
#     "node_name" : "aks-agentpool-23035252-vmss000005",
#     "prometheus_endpoint": "https://defaultazuremonitorworkspace-neu-b44y.northeurope.prometheus.monitor.azure.com"
# }

# node = AKSNode(name = "myaksclsuter", model = ComputeServer_STATIC_IMP(),  carbon_intensity_provider=None, auth_object=auth_params, resource_selectors=resource_selectors, metadata=metadata)

# aggregation = MetricAggregationType.AVERAGE

#print(node)
#node.fetch_resources()

#print(node.fetch_observations(interval="PT15M", timespan="PT1H"))

#print(node.calculate())


# pod_resource_selectors = {
#     "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
#     "resource_group": "sus-aks-lab",
#     "cluster_name": "sus-aks-lab",
#     #"labels" : {"name" : "keda-operator"},
#     "namespace" : "keda",
#     "prometheus_endpoint": "https://defaultazuremonitorworkspace-neu-b44y.northeurope.prometheus.monitor.azure.com"
# }

# pod = AKSPod(name = "myakspod", model = ComputeServer_STATIC_IMP(),  carbon_intensity_provider=None, auth_object=auth_params, resource_selectors=pod_resource_selectors, metadata=metadata)

# print(pod.fetch_resources())
# print (pod.fetch_observations(interval="PT15M", timespan="PT1H"))
# print(pod.calculate())

"""
print(vm.fetch_resources())


data = {
    "metric_1": 1.23,
    "metric_2": 4.56,
    "metric_3": 7.89
}

#static method
MetricsExporter.start_http_server(port=8000)
while(True):

    vm.fetch_observations(aggregation=aggregation, interval="PT15M", timespan="PT1H")
    print(vm.observations)
    data = vm.calculate()
    print(data)

    
    exporter = MetricsExporter(data)
    exporter.to_csv('metrics.csv')
    exporter.to_json('metrics.json')
    exporter.to_prometheus()

    time.sleep(2)



request_json = {
    "app_name": "toto",
    "components": [
        {
            "type": "AzureVM",
            "resource_selectors": {
                "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
                "resource_group": "webapprename",
                "name": "tototatar"
            }
        },
        {
            "type": "AKSNode",
            "resource_selectors": {
                ...
            }
        }
    ],
    "interval": "PT15M",
    "timespan": "PT1H"
}
"""