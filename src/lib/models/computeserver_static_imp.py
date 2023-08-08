from lib.ief.core import ImpactModelPluginInterface, SCIImpactMetricsInterface
from typing import Dict, List

from datetime import timedelta
import re
from isoduration import parse_duration

class ComputeServer_STATIC_IMP(ImpactModelPluginInterface):
    def __init__(self):
        super().__init__()
        self.name = "computeserver_static_imp"
        self.static_params = None

    def model_identifier(self) -> str:
        return self.name

    async def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactModelPluginInterface':
        self.name = name
        self.static_params = static_params
        return self

    def authenticate(self, auth_params: Dict[str, object]) -> None:
        pass


    def calculate_ecpu(self, cpu_utilization_during_timespan, tdp=200, timespan='PT1H', core_count=2):
        if tdp <= 0:
            raise ValueError("TDP must be a positive number")
        if cpu_utilization_during_timespan <= 0:
            tdp_coefficient = 0.12
        elif cpu_utilization_during_timespan <= 10:
            tdp_coefficient = 0.32
        elif cpu_utilization_during_timespan <= 50:
            tdp_coefficient = 0.75
        else:
            tdp_coefficient = 1.02
        power_consumption = tdp * tdp_coefficient
        duration = parse_duration(timespan)
        duartion_in_hours = float(duration.time.hours)
        energy_consumption = core_count * (power_consumption * duartion_in_hours / 1000) # W * H / 1000 = KWH
        return energy_consumption


    def calculate_emem(self, ram_size_gb_during_timespan):
        if ram_size_gb_during_timespan <= 0:
            raise ValueError("RAM size must be a positive number")

        energy_per_gb = 0.38  # kWh per GB

        energy_consumption = energy_per_gb * ram_size_gb_during_timespan # kWh per GB * GB = kWh
        return energy_consumption


    def calculate_egpu(self, gpu_util) -> float:
        if gpu_util is not None and 0 <= gpu_util <= 100:
            # Calculate the power consumed by the GPU using a linear model
            pg = 0.2 * gpu_util + 10  # 10 W is the idle power consumption of the GPU

            # Calculate the energy consumed by the GPU over the past hour
            egpu = pg * 3600 / 1000  # Convert from Ws to kWh

            return egpu

        return 0

    def calculate_m(self) -> float:
        # Code to calculate M metric data
        return 40.0  # Example value

    def calculate(self, observations, carbon_intensity: float = 100, metadata : dict [str, str] = {}) -> dict[str, SCIImpactMetricsInterface]:
        # Create an empty dictionary to store the metrics for each resource
        resource_metrics = {}

        # Iterate over the observations for each resource
        for resource_name, resource_observations in observations.items():
            # Get the CPU utilization, memory utilization, and GPU utilization from the observations
            cpu_util = resource_observations.get("percentage_cpu", 0)
            mem_util = resource_observations.get("percentage_memory", 0)
            gpu_util = resource_observations.get("percentage_gpu", 0)

            # Calculate the E-CPU, E-Mem, and E-GPU metrics
            ecpu = self.calculate_ecpu(cpu_util)
            emem = self.calculate_emem(mem_util)
            egpu = self.calculate_egpu(gpu_util)

            # Calculate the M and SCI metrics
            i = carbon_intensity
            m = self.calculate_m()

            # Create a dictionary with the metric names and values for this resource
            impact_metrics = {
                'type': 'azurevm',
                'name': resource_name,
                'model': self.name,
                'E_CPU': float(ecpu),
                'E_MEM': float(emem),
                'E_GPU': float(egpu),
                'E': float(ecpu + emem + egpu),
                'I': float(i),
                'M': float(m),
                'SCI': float(((ecpu + emem + egpu) * i) + m)
            }
            print(impact_metrics)
            resource_metrics[resource_name] = SCIImpactMetricsInterface(metrics=impact_metrics, metadata={"resource_name": resource_name}, observations=resource_observations, components_list=[])

            # Remove any metrics with None values
            #resource_metrics[resource_name] = {k: v for k, v in resource_metrics[resource_name].items() if v is not None}

        # Create an instance of the ImpactMetricInterface with the calculated metrics

        print("coucou")
        #metrics.metrics = resource_metrics


        return resource_metrics