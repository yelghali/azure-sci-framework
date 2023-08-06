from typing import Dict, List
from lib.ief.core import ImpactMetricInterface
from lib.components.azure_base import AzureImpactNode
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.compute.models import VirtualMachine


class AzureVM(AzureImpactNode):
    def __init__(self, model, carbon_intensity_provider, auth_object, resource_selectors, metadata):
        super().__init__(model, carbon_intensity_provider, auth_object, resource_selectors, metadata)
        self.name = "AzureVM"
        self.resources = {}

    def list_supported_skus(self):
        return ["D3V4"]
    
    def fetch_resources(self) -> Dict[str, VirtualMachine]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group = self.resource_selectors.get("resource_group", None) 
        name = self.resource_selectors.get("name", None) 
        tags = self.resource_selectors.get("tags", None) 
        vms = {}

        compute_client = ComputeManagementClient(self.credential, subscription_id)

        if name and resource_group:
            vm = compute_client.virtual_machines.get(resource_group, name)
            vms[vm.name] = vm
        elif tags:
            filter_str = " and ".join([f"tagname eq '{k}' and tagvalue eq '{v}'" for k, v in tags.items()])
            for vm in compute_client.virtual_machines.list_all(filter=filter_str):
                vms[vm.name] = vm
        else:
            for vm in compute_client.virtual_machines.list_all():
                vms[vm.name] = vm

        self.resources = vms
        return self.resources



    def fetch_observations(self, aggregation: str, timespan : str, interval: str) -> Dict[str, object]:
        """
        Fetches a dictionary of metric observations from Azure Monitor.

        :param metric_names: A list of metric names to fetch.
        :param aggregation: The aggregation type to use.
        :param interval: The time interval to fetch data for.
        :param tags: A dictionary of tags to filter by.
        :return: A dictionary containing metric observations.
        """
        observations = {}
        subscription_id = self.resource_selectors.get("subscription_id", None)
        monitor_client = MonitorManagementClient(self.credential, subscription_id)

        print(self.resources)

        for resource_name, resource  in self.resources.items():
            if resource.type == 'Microsoft.Compute/virtualMachines':
                vm_id = resource.id
                vm_name = resource.name
                cpu_utilization = None
                memory_utilization = None
                gpu_utilization = None
                # Fetch CPU utilization
                cpu_data = monitor_client.metrics.list(
                    resource_uri=vm_id,
                    metricnames='Percentage CPU',
                    aggregation=aggregation,
                    interval=interval,
                    timespan=timespan
                )

                cpu_util_list = []
                if cpu_data.value:
                    metric_data = cpu_data.value[0]
                    for time_series_element in metric_data.timeseries:
                        for metric_value in time_series_element.data:
                            cpu_util_list.append(metric_value.average)

                cpu_utilization = sum(cpu_util_list) / len(cpu_util_list) if len(cpu_util_list) > 0 else None

                print(cpu_utilization)
    
                # Fetch memory utilization
                memory_data = monitor_client.metrics.list(
                    resource_uri=vm_id,
                    metricnames='Available Memory Bytes',
                    aggregation=aggregation,
                    interval=interval,
                    timespan=timespan
                )
                if memory_data.value:
                    metric_data = memory_data.value[0]
                    for time_series_element in metric_data.timeseries:
                        for metric_value in time_series_element.data:
                            memory_utilization = metric_value.average

                print(memory_utilization)

                # Fetch GPU utilization (if available)
                if resource.resources is not None:
                    for extension in resource.resources:
                        # Fetch GPU utilization (if available)
                        if extension.type == 'Microsoft.Compute/virtualMachines/extensions' and extension.name == 'NVIDIA-GPU-Extension':
                            gpu_data = monitor_client.metrics.list(
                                resource_uri=extension.id,
                                metricnames='GPU Utilization',
                                aggregation=aggregation,
                                interval=interval,
                                timespan=timespan
                            )
                            if gpu_data.value:
                                metric_data = gpu_data.value[0]
                                for time_series_element in metric_data.timeseries:
                                    for metric_value in time_series_element.data:
                                        gpu_utilization = metric_value.average

                print(gpu_utilization)

                observations[vm_name] = {
                    'cpu_utilization': cpu_utilization,
                    'memory_utilization': memory_utilization,
                    'gpu_utilization': gpu_utilization
                }

        return observations     

    def calculate(self, observations=None):
        return self.inner_model.calculate(observations)

    def lookup_static_params(self) -> Dict[str, object]:
        return {}