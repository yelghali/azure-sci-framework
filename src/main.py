# sample instanciation with prints of AzureVM class
import sys
from azure.mgmt.monitor.models import MetricAggregationType


sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP

auth_params = {
    "tenant_id": "12345678-1234-1234-1234-123456789012",
    "client_id": "12345678-1234-1234-1234-123456789012",
    "client_secret": "12345678-1234-1234-1234-123456789012"
}

resource_selectors = {
    "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
    "resource_group": "webapprename",
    "name": "tototatar"
}

metadata = {
    "region": "westeurope"
}

vm = AzureVM(ComputeServer_STATIC_IMP(), None, auth_params, resource_selectors=resource_selectors, metadata=metadata)

aggregation = MetricAggregationType.AVERAGE


print(vm.fetch_resources())
vm.fetch_observations(aggregation=aggregation, interval="PT15M", timespan="PT1H")
print(vm.observations)
print(vm.calculate())
