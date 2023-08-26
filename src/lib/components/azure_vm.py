from typing import Dict, List, Tuple
from lib.ief.core import SCIImpactMetricsInterface
from lib.components.azure_base import AzureImpactNode
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.compute.models import VirtualMachine

from azure.mgmt.monitor.models import MetricAggregationType

import csv

import time
import asyncio

import itertools

aggregation = MetricAggregationType.AVERAGE #for monitoring queries

semaphore_max = 5 # to avoid throttling ; this is the max number of concurrent queries for Azure Monitor


class AzureVM(AzureImpactNode):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval="PT5M", timespan="PT1H"):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval, timespan)
        self.type = "azure.compute.vm"
        self.resources = {}
        self.observations = {}
        self.static_params = {}
        self.aggregation = aggregation

    def list_supported_skus(self):
        return ["D3V4"]
    
    async def fetch_resources(self) -> Dict[str, object]:
        #print(self.resource_selectors)
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


    async def fetch_cpu_memory_utilization(self, semaphore, vm_id: str, instance_memory: int, monitor_client: MonitorManagementClient) -> Tuple[float, float]:
        """
        Fetches the average CPU and memory utilization for a virtual machine.

        :param vm_id: The ID of the virtual machine.
        :param instance_memory: The amount of memory allocated to the virtual machine in GB.
        :param monitor_client: The Azure Monitor client.
        :return: A tuple containing the average CPU utilization and memory utilization in GB.
        """

        # Acquire the semaphore before running the query
        async with semaphore:
            retry_count = 0
            while retry_count < 7:
                try:
                    cpu_memory_data = monitor_client.metrics.list(
                        resource_uri=vm_id,
                        metricnames="Percentage CPU,Available Memory Bytes",
                        aggregation=self.aggregation,
                        interval=self.interval,
                        timespan=self.timespan
                    )
                    break
                except:
                    retry_count += 1
                    await asyncio.sleep(5 ** retry_count)
                    continue

        total_cpu_utilization = 0
        data_points = 0

        total_memory_allocated = instance_memory

        average_consumed_memory_gb_items = []
        for metric in cpu_memory_data.value:
            if metric.name.localized_value == 'Percentage CPU':
                for time_series in metric.timeseries:
                    for data in time_series.data:
                        if data.average is not None:
                            total_cpu_utilization += data.average
                            data_points += 1
            elif metric.name.localized_value in ['Available Memory Bytes', 'Available Memory Bytes (Preview)']:
                for time_series in metric.timeseries:
                    for data in time_series.data:
                        if data.average is not None:
                            datapoint_average_consumed_memory_gb = total_memory_allocated - (data.average / 1024 ** 3)
                            average_consumed_memory_gb_items.append(datapoint_average_consumed_memory_gb)

        average_cpu_utilization = total_cpu_utilization / data_points if data_points > 0 else 0
        cpu_utilization = average_cpu_utilization

        average_consumed_memory_gb_during_timespan = sum(average_consumed_memory_gb_items) / len(average_consumed_memory_gb_items) if average_consumed_memory_gb_items else 0
        memory_utilization = average_consumed_memory_gb_during_timespan

        return cpu_utilization, memory_utilization


    async def fetch_gpu_utilization(self, resource: object, monitor_client: MonitorManagementClient) -> float:
        """
        Fetches the average GPU utilization for a virtual machine.

        :param resource: The virtual machine resource.
        :param monitor_client: The Azure Monitor client.
        :return: The average GPU utilization.
        """
        gpu_utilization = 0
        if resource.resources is not None:
            for extension in resource.resources:
                if extension.type == 'Microsoft.Compute/virtualMachines/extensions' and extension.name == 'NVIDIA-GPU-Extension':
                    gpu_data = monitor_client.metrics.list(
                        resource_uri=extension.id,
                        metricnames='GPU Utilization',
                        aggregation=self.aggregation,
                        interval=self.interval,
                        timespan=self.timespan
                    )

                    if gpu_data.value:
                        total_gpu_utilization = 0
                        data_points = 0
                        for metric in gpu_data.value:
                            for time_series in metric.timeseries:
                                for data in time_series.data:
                                    if data.average is not None:
                                        total_gpu_utilization += data.average
                                        data_points += 1

                        average_gpu_utilization = total_gpu_utilization / data_points if data_points > 0 else 0
                        gpu_utilization = average_gpu_utilization

        return gpu_utilization


    async def fetch_observations(self) -> Dict[str, object]:
        """
        Fetches a dictionary of metric observations from Azure Monitor.

        :return: A dictionary containing metric observations.
        """
        subscription_id = self.resource_selectors.get("subscription_id", None)
        monitor_client = MonitorManagementClient(self.credential, subscription_id)

        if self.resources == {} or self.resources == None: await self.fetch_resources()
        if self.static_params == {} or self.static_params == None: await self.lookup_static_params()

        # Create a semaphore with an initial value of 3
        semaphore = asyncio.Semaphore(semaphore_max) # to avoid throttling ; this is the max number of concurrent queries for Azure Monitor

        tasks = []
        resource_names = []
        for resource_name, resource in self.resources.items():
            if resource.type == 'Microsoft.Compute/virtualMachines':
                vm_id = resource.id
                vm_name = resource.name
                instance_memory = self.static_params[resource_name]['instance_memory']

                task = asyncio.create_task(self.fetch_cpu_memory_utilization(semaphore, vm_id, instance_memory, monitor_client))
                tasks.append(task)

                task = asyncio.create_task(self.fetch_gpu_utilization(resource, monitor_client))
                tasks.append(task)

                resource_names.append(resource_name)

        results = await asyncio.gather(*tasks)

        for i in range(0, len(results), 2):
            cpu_utilization, memory_utilization = results[i]
            gpu_utilization = results[i+1]

            resource_name = resource_names[i//2]
            self.observations[resource_name] = {
                'average_cpu_percentage': cpu_utilization,
                'average_memory_gb': memory_utilization,
                'average_gpu_percentage': gpu_utilization
            }

        return self.observations

 

    async def calculate(self, carbon_intensity = 100) -> dict[str : SCIImpactMetricsInterface]:
        # if self.resources == {}: call fetch_resources
        if self.resources == {} or self.resources == None:
            await self.fetch_resources()
        # if self.static_params == {}: call lookup_static_params
        if self.static_params == {} or self.static_params == None:
            await self.lookup_static_params()

        #always get updated observations
        await self.fetch_observations()

        return await self.inner_model.calculate(observations=self.observations, carbon_intensity=self.carbon_intensity_provider, timespan=self.timespan, interval= self.interval, metadata=self.metadata, static_params=self.static_params)


    async def get_vm_sku_tdp(self, vm_sku: str) -> int:
        # Get TDP for the VM sku, from the static data file
        vm_sku_tdp = 180  # default value for unknown VM SKUs
        with open('lib/static_data/azure_vm_tdp.csv', 'r') as f:
            for line in f:
                if vm_sku in line:
                    vm_sku_tdp = line.split(',')[1]
                    break
        return vm_sku_tdp


    async def get_vm_resources(self, vm_sku: str) -> Tuple[int, float, float]:
        # Get RR, TR and instance memory for the VM sku, from the static data file
        rr = 2  # vCPUs
        total_vcpus = 16
        instance_memory = 0.0
        with open('lib/static_data/ccf_azure_instances.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            vm_sku_short = ''.join(vm_sku.split('_')[1:])
            for row in reader:
                if row['Virtual Machine'].replace(" ", "").lower() == vm_sku_short.replace(" ", "").lower():
                    rr = int(row['Instance vCPUs'])
                    total_vcpus = float(row['Platform vCPUs (highest vCPU possible)'])
                    instance_memory = float(row['Instance Memory'])
                    break
        return rr, total_vcpus, instance_memory


    async def get_vm_te(self, vm_sku: str) -> float:
        # Get TE for the VM sku, from the static data file
        te = 1200
        with open('lib/static_data/ccf_coefficients-azure-embodied.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            vm_sku_short = vm_sku.split('_')[1]
            for row in reader:
                if row['type'].replace(" ", "").lower() == vm_sku_short.replace(" ", "").lower():
                    te = float(row['total'])
                    break
        return te


    async def lookup_static_params(self) -> Dict[str, object]:

        if self.resources == {} or self.resources == None: await self.fetch_resources()

        # Create a list of coroutines to run concurrently using a list comprehension
        coroutines = [
            (
                self.get_vm_sku_tdp(resource.hardware_profile.vm_size),
                self.get_vm_resources(resource.hardware_profile.vm_size),
                self.get_vm_te(resource.hardware_profile.vm_size)
            )
            for resource_name, resource in self.resources.items()
            if resource.type == 'Microsoft.Compute/virtualMachines'
        ]

        # Run the coroutines concurrently using asyncio.gather
        results = await asyncio.gather(*[coro for coro in itertools.chain(*coroutines)])

        # Process the results and update the static_params dictionary
        i = 0
        for resource_name, resource in self.resources.items():
            if resource.type == 'Microsoft.Compute/virtualMachines':
                vm_name = resource.name
                vm_sku_tdp = results[i]
                rr, total_vcpus, instance_memory = results[i+1]
                te = results[i+2]

                self.static_params[vm_name] = {
                    'vm_sku': resource.hardware_profile.vm_size,
                    'vm_sku_tdp': vm_sku_tdp,
                    'rr': rr,
                    'total_vcpus': total_vcpus,
                    'te': te,
                    'instance_memory': instance_memory
                }

                i += 3

        return self.static_params



