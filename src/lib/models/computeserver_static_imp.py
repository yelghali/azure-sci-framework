from lib.ief.core import ImpactModelPluginInterface, SCIImpactMetricsInterface
from typing import Dict, List

from datetime import timedelta
import re
from isoduration import parse_duration
import warnings

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

    #TODO : core_count variable
    def calculate_ecpu(self, cpu_utilization_during_timespan, tdp=200, timespan='PT1H', core_count=2):
        if tdp <= 0 or core_count <= 0:
            warnings.warn("TDP must be a positive number")
            return 0
        
        if cpu_utilization_during_timespan == 0:
            tdp_coefficient = 0
        elif cpu_utilization_during_timespan > 0 and cpu_utilization_during_timespan < 10:
            tdp_coefficient = 0.12
        elif cpu_utilization_during_timespan >= 10 and cpu_utilization_during_timespan < 50:
            tdp_coefficient = 0.32
        elif cpu_utilization_during_timespan >= 50 and cpu_utilization_during_timespan < 100:
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
            warnings.warn("RAM size must be a positive number")
            return 0

        energy_per_gb = 0.38  # kWh per GB

        energy_consumption = energy_per_gb * ram_size_gb_during_timespan # kWh per GB * GB = kWh
        return energy_consumption


    # same for ecpu formula ; TDDO : same coefficient for both ?
    #TODO : gpu_count variable
    def calculate_egpu(self, gpu_utilization_during_timespan, tdp=250, timespan='PT1H', gpu_count=2):
        if tdp <= 0 or gpu_count <= 0:
            raise ValueError("TDP must be a positive number")
        

        if gpu_utilization_during_timespan == 0:
            tdp_coefficient = 0
        elif gpu_utilization_during_timespan > 0 and gpu_utilization_during_timespan < 10:
            tdp_coefficient = 0.12
        elif gpu_utilization_during_timespan >= 10 and gpu_utilization_during_timespan < 50:
            tdp_coefficient = 0.32
        elif gpu_utilization_during_timespan >= 50 and gpu_utilization_during_timespan < 100:
            tdp_coefficient = 0.75
        else:
            tdp_coefficient = 1.02


        power_consumption = tdp * tdp_coefficient
        duration = parse_duration(timespan)
        duartion_in_hours = float(duration.time.hours)
        energy_consumption = gpu_count * (power_consumption * duartion_in_hours / 1000) # W * H / 1000 = KWH
        return energy_consumption

    def calculate_m(self, timespan='PT1H' ) -> float:
        # TE: Embodied carbon estimates for the servers from the Cloud Carbon Footprint Coefficient Data Set
        te = 0.5  # kgCO2e/hour

        # TR: Time reserved for the hardware
        tr = 1  # hour
        duration = parse_duration(timespan)
        duartion_in_hours = float(duration.time.hours)
        tr = duartion_in_hours

        # EL: Expected lifespan of the equipment
        el = 35040  # hours (4 years)

        # RR: Resources reserved for use by the software
        rr = 2  # vCPUs

        # TR: Total number of resources available
        total_vcpus = 16

        # Calculate M using the equation M = TE * (TR/EL) * (RR/TR)
        m = te * (tr / el) * (rr / total_vcpus)

        return m

    def calculate(self, observations, carbon_intensity: float = 100, timespan : str = "PT1H", interval = 'PT5M', metadata : dict [str, str] = {}, static_params : dict[str, str]= {} ) -> dict[str, SCIImpactMetricsInterface]:
        # Create an empty dictionary to store the metrics for each resource
        resource_metrics = {}


        # Iterate over the observations for each resource
        for resource_name, resource_observations in observations.items():
            # Get the CPU utilization, memory utilization, and GPU utilization from the observations
            cpu_util = resource_observations.get("average_cpu_percentage", 0)
            mem_util = resource_observations.get("average_memory_gb", 0)
            gpu_util = resource_observations.get("average_gpu_percentage", 0)

            tdp = static_params.get(resource_name, {}).get("vm_sku_tdp", 200)

            # Calculate the E-CPU, E-Mem, and E-GPU metrics
            ecpu = self.calculate_ecpu(cpu_util, timespan=timespan, tdp=tdp)
            emem = self.calculate_emem(mem_util) #memory model uses only the average memory utilization in GB (calculated for the given timespan))
            egpu = self.calculate_egpu(gpu_util, timespan=timespan, tdp=tdp)

            # Calculate the M and SCI metrics
            i = carbon_intensity
            m = self.calculate_m(timespan=timespan)

            # Create a dictionary with the metric names and values for this resource
            impact_metrics = {
                'type': 'azurevm',
                'name': resource_name,
                'model': self.name,
                'timespan' : timespan,
                'interval' : interval,
                'E_CPU': float(ecpu),
                'E_MEM': float(emem),
                'E_GPU': float(egpu),
                'E': float(ecpu) + float(emem) + float(egpu),
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