from typing import Dict, List
from lib.ief.core import SCIImpactMetricsInterface
from lib.components.azure_base import AzureImpactNode
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.compute.models import VirtualMachine

from azure.mgmt.monitor.models import MetricAggregationType

class AzureVM(AzureImpactNode):
    def __init__(self, model, carbon_intensity_provider, auth_object, resource_selectors, metadata):
        super().__init__(model, carbon_intensity_provider, auth_object, resource_selectors, metadata)
        self.type = "azurevm"
        self.resources = {}
        self.observations = {}

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

    aggregation = MetricAggregationType.AVERAGE

    def fetch_observations(self, aggregation: str = aggregation, timespan : str = "PT1H", interval: str = "PT15M") -> Dict[str, object]:
        """
        Fetches a dictionary of metric observations from Azure Monitor.

        :param metric_names: A list of metric names to fetch.
        :param aggregation: The aggregation type to use.
        :param interval: The time interval to fetch data for.
        :return: A dictionary containing metric observations.
        """
        subscription_id = self.resource_selectors.get("subscription_id", None)
        monitor_client = MonitorManagementClient(self.credential, subscription_id)

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

                # Calculate the average percentage CPU utilization
                total_cpu_utilization = 0
                data_points = 0
                for metric in cpu_data.value:
                    for time_series in metric.timeseries:
                        for data in time_series.data:
                            if data.average is not None:
                                total_cpu_utilization += data.average
                                data_points += 1

                average_cpu_utilization = total_cpu_utilization / data_points
                cpu_utilization = average_cpu_utilization
                #print(cpu_utilization)
    
                # Fetch memory utilization (calculte from available memory since there is no metric for used memory in Azure Monitor)
                memory_data = monitor_client.metrics.list(
                    resource_uri=vm_id,
                    metricnames='Available Memory Bytes',
                    aggregation=aggregation,
                    interval=interval,
                    timespan=timespan
                )
                
                # Calculate the total memory allocated to the virtual machine in bytes
                total_memory_allocated = 4  #GB ; TODO: Fetch from VM SKU


                # Calculate the average available memory in GB
                average_consumed_memory_gb_items =  []
                average_consumed_memory_gb_during_timespan = 0
                for metric in memory_data.value:
                    for time_series in metric.timeseries:
                        for data in time_series.data:
                            if data.average is not None:
                                datapoint_average_consumed_memory_gb = total_memory_allocated - (data.average / 1024 ** 3) # /1024 ** 3 converts bytes to GB
                                average_consumed_memory_gb_items.append(datapoint_average_consumed_memory_gb)

                average_consumed_memory_gb_during_timespan = sum(average_consumed_memory_gb_items) / len(average_consumed_memory_gb_items)
                print(average_consumed_memory_gb_items)
                print(average_consumed_memory_gb_during_timespan)
                print(total_memory_allocated)
                memory_utilization = average_consumed_memory_gb_during_timespan
                #print(memory_utilization)

                # Fetch GPU utilization (if available)
                gpu_util_list = []
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
                                        if metric_value.average is not None:
                                            gpu_util_list.append(float(metric_value.average))
                    gpu_utilization = sum(gpu_util_list) / len(gpu_util_list) if len(gpu_util_list) > 0 else None

                #print(gpu_utilization)

                self.observations[vm_name] = {
                    'percentage_cpu': cpu_utilization,
                    'percentage_memory': memory_utilization,
                    'percentage_gpu': gpu_utilization
                }

        return self.observations     

    def calculate(self, carbon_intensity = 100) -> dict[str : SCIImpactMetricsInterface]:
        return self.inner_model.calculate(self.observations, carbon_intensity=100)

    def lookup_static_params(self) -> Dict[str, object]:
        return {}