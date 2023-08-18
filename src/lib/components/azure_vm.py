from typing import Dict, List
from lib.ief.core import SCIImpactMetricsInterface
from lib.components.azure_base import AzureImpactNode
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.compute.models import VirtualMachine

from azure.mgmt.monitor.models import MetricAggregationType

import csv

aggregation = MetricAggregationType.AVERAGE #for monitoring queries


class AzureVM(AzureImpactNode):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval="PT5M", timespan="PT1H"):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval, timespan)
        self.type = "azurevm"
        self.resources = {}
        self.observations = {}
        self.static_params = {}

    def list_supported_skus(self):
        return ["D3V4"]
    
    def fetch_resources(self) -> Dict[str, VirtualMachine]:
        print(self.resource_selectors)
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


    #def fetch_observations(self, aggregation: str = aggregation, timespan : str = "PT1H", interval: str = "PT15M") -> Dict[str, object]:
    def fetch_observations(self) -> Dict[str, object]:
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
                    interval=self.interval,
                    timespan=self.timespan
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

                if data_points > 0 :
                    average_cpu_utilization = total_cpu_utilization / data_points
                else : average_cpu_utilization = 0
                cpu_utilization = average_cpu_utilization
                #print(cpu_utilization)
    
                # Fetch memory utilization (calculte from available memory since there is no metric for used memory in Azure Monitor)
                memory_data = monitor_client.metrics.list(
                    resource_uri=vm_id,
                    metricnames='Available Memory Bytes',
                    aggregation=aggregation,
                    interval=self.interval,
                    timespan=self.timespan
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

                if len(average_consumed_memory_gb_items) > 0 :
                    average_consumed_memory_gb_during_timespan = sum(average_consumed_memory_gb_items) / len(average_consumed_memory_gb_items)
                else : average_consumed_memory_gb_during_timespan = 0
                memory_utilization = average_consumed_memory_gb_during_timespan

                # Fetch GPU utilization (if available)
                gpu_utilization = 0
                if resource.resources is not None:
                    for extension in resource.resources:
                        # Fetch GPU utilization (if available)
                        if extension.type == 'Microsoft.Compute/virtualMachines/extensions' and extension.name == 'NVIDIA-GPU-Extension':
                            gpu_data = monitor_client.metrics.list(
                                resource_uri=extension.id,
                                metricnames='GPU Utilization',
                                aggregation=aggregation,
                                interval=self.interval,
                                timespan=self.timespan
                            )
                            
                            if gpu_data.value:
                                total_gpu_utilization = 0
                                data_points = 0
                                # Calculate the average percentage GPU utilization
                                for metric in cpu_data.value:
                                    for time_series in metric.timeseries:
                                        for data in time_series.data:
                                            if data.average is not None:
                                                total_cpu_utilization += data.average
                                                data_points += 1

                                if data_points > 0 : 
                                    average_gpu_utilization = total_gpu_utilization / data_points 
                                else : 
                                    average_gpu_utilization = 0
                                gpu_utilization = average_gpu_utilization


                self.observations[vm_name] = {
                    'average_cpu_percentage': cpu_utilization,
                    'average_memory_gb': memory_utilization,
                    'average_gpu_percentage': gpu_utilization
                }

        return self.observations     

    def calculate(self, carbon_intensity = 100) -> dict[str : SCIImpactMetricsInterface]:
        self.fetch_resources()
        self.fetch_observations()
        self.lookup_static_params()
        return self.inner_model.calculate(observations=self.observations, carbon_intensity=100, timespan=self.timespan, interval= self.interval, metadata=self.metadata, static_params=self.static_params)

    def lookup_static_params(self) -> Dict[str, object]:
        #get TDP for the VM sku, from the static data file

        for resource_name, resource  in self.resources.items():
            if resource.type == 'Microsoft.Compute/virtualMachines':
                #print(resource.os_profile)
                print(resource.hardware_profile)

                vm_id = resource.id
                vm_name = resource.name
                vm_sku = resource.hardware_profile.vm_size

                vm_sku_tdp = 180 #default value for unknown VM SKUs

                #get TDP for the VM sku, from the static data file
                with open('lib/static_data/azure_vm_tdp.csv', 'r') as f:
                    for line in f:
                        if vm_sku in line:
                            vm_sku_tdp = line.split(',')[1]
                            break


                # RR: Resources reserved for use by the software
                rr = 2  # vCPUs

                # TR: Total number of resources available
                total_vcpus = 16

                
                # Load the CSV file
                with open('lib/static_data/ccf_azure_instances.csv', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    vm_sku_short = vm_sku.split('_')[1]
                    # Find the row that matches the VM series and size
                    for row in reader:
                        #if row['Series'] == vm_series and row['VM'] == vm_sku:
                        if row['Virtual Machine'].replace(" ", "").lower() == vm_sku_short.replace(" ", "").lower():
                            # Extract the rr and total_vcpus values
                            rr = int(row['Instance vCPUs'])
                            total_vcpus = int(row['Platform vCPUs (highest vCPU possible)'])

                            break


                
                # TE : Total embodied emissions for the VM hardware
                te = 1200
                
                # Load the CSV file
                with open('lib/static_data/ccf_coefficients-azure-embodied.csv', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    vm_sku_short = vm_sku.split('_')[1]
                    # Find the row that matches the VM series and size
                    for row in reader:
                        #if row['Series'] == vm_series and row['VM'] == vm_sku:
                        if row['type'].replace(" ", "").lower() == vm_sku_short.replace(" ", "").lower():
                            # Extract the rr and total_vcpus values
                            te = float(row['total'])

                            break

            self.static_params[vm_name] = {
                'vm_sku': vm_sku,
                'vm_sku_tdp': vm_sku_tdp,
                'rr': rr,
                'total_vcpus': total_vcpus,
                'te': te
            }    
        return self.static_params