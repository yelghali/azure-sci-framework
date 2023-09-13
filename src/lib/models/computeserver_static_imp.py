from lib.ief.core import ImpactModelPluginInterface, SCIImpactMetricsInterface
from lib.ief.core import CarbonIntensityPluginInterface
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


    def calculate_ecpu(self, cpu_utilization_during_timespan, tdp=200, timespan='PT1H', core_count=2, tr=None):
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


        if tr is None:
        # we assume the software has been running during the whole timespan
        # for practical calculation, we convert to minutes first, to avoid gettting 0 hours for small durations as 5 minutes using direct hours conversion.
            duration = parse_duration(timespan)
            duration_in_minutes = float(duration.time.minutes)
            duration_in_hours = duration_in_minutes / 60.0

            if hasattr(duration.time, 'hours'):
                duration_in_hours += float(duration.time.hours)

            if hasattr(duration.time, 'days'):
                duration_in_hours += float(duration.time.days) * 24.0
            
        else:
            duration_in_hours = tr
        
        
        energy_consumption = core_count * (power_consumption * duration_in_hours / 1000) # W * H / 1000 = KWH
        return energy_consumption


    def calculate_emem(self, ram_size_gb_during_timespan, timespan='PT1H'):
        if ram_size_gb_during_timespan <= 0:
            warnings.warn("RAM size must be a positive number")
            return 0

        duration = parse_duration(timespan)
        duration_in_minutes = float(duration.time.minutes)
        duration_in_hours = duration_in_minutes / 60.0

        if hasattr(duration.time, 'hours'):
            duration_in_hours += float(duration.time.hours)

        if hasattr(duration.time, 'days'):
            duration_in_hours += float(duration.time.days) * 24.0


        energy_per_gb = 0.38  # Watt per GB

        energy_consumption = energy_per_gb * ram_size_gb_during_timespan / 1000 # kWh per GB * GB = kWh
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

    def calculate_m(self, timespan='PT1H', rr = 2, total_vcpus = 20, te = 1200, tr = None ) -> float:
        # TE: Embodied carbon estimates for the servers from the Cloud Carbon Footprint Coefficient Data Set
        te = te  # kgCO2e
        te_g = te * 1000  # gCO2e


        # TR: Time reserved for use by the software ; if not set we'll assume the software was always running for the given timespan
        if tr is None: #we assume software was always running for the given timespan
            warnings.warn(f"TR is not set. we assume software was always running for the given timespan : {timespan}")
            tr = 1  # initial value is 1 hour , if non is found below
            
            # we convert to minutes first, to avoid gettting 0 hours for small durations as 5 minutes using direct hours conversion.
            duration = parse_duration(timespan)
            duration_in_minutes = float(duration.time.minutes)
            duration_in_hours = duration_in_minutes / 60.0

            if hasattr(duration.time, 'hours'):
                duration_in_hours += float(duration.time.hours)

            if hasattr(duration.time, 'days'):
                duration_in_hours += float(duration.time.days) * 24.0


            if duration_in_hours : tr = duration_in_hours

        else :
            tr = tr

        # EL: Expected lifespan of the equipment
        el = 35040  # hours (4 years)

        # RR: Resources reserved for use by the software
        rr = rr # vCPUs

        # TR: Total number of resources available
        total_vcpus = total_vcpus

        print("tr : " + str(tr))
        #print("duartion_in_hours : " + str(duration_in_hours))
        print("rr : " + str(rr))
        print("total_vcpus : " + str(total_vcpus))
        print("te Kgco2 : " + str(te))
        print("te gco2 : " + str(te_g))
        print("el : " + str(el))

        # Calculate M using the equation M = TE * (TR/EL) * (RR/TR)
        m = te_g * (tr / el) * (rr / total_vcpus)

        return m

    async def calculate(self, observations, carbon_intensity: CarbonIntensityPluginInterface= None, timespan : str = "PT1H", interval = 'PT5M', metadata : dict [str, object] = {}, static_params : dict[str, object]= {} ) -> dict[str, SCIImpactMetricsInterface]:
        # Create an empty dictionary to store the metrics for each resource
        resource_metrics = {}

        if carbon_intensity is None:
            warnings.warn("Carbon intensity provider is not set. Using static value of 100 gCO2e/kWh")
            CI = 100
        else:
            CI = await carbon_intensity.get_current_carbon_intensity()
            CI = CI["value"]

        # Iterate over the observations for each resource
        for resource_name, resource_observations in observations.items():
            # Get the CPU utilization, memory utilization, and GPU utilization from the observations
            cpu_util = resource_observations.get("average_cpu_percentage", 0)
            mem_util = resource_observations.get("memory_gb", 0)
            gpu_util = resource_observations.get("average_gpu_percentage", 0)

            tdp = static_params.get(resource_name, {}).get("vm_sku_tdp", 200) or 200 # used for E-CPU and E-GPU metrics

            # resources resrved, aka cpu core used by software
            # if we have cpucores used from observations, we use it 
            rr = resource_observations.get("rr", None)
            if rr is None:
                rr = static_params.get(resource_name, {}).get("instance_vcpus", 2) or 2 #used to calculate E and M metrics
                warnings.warn(f"cpuCores (rr) is not set. we use rr = the vcpu allocated capacity, instead of the actual vcpu used : rr = instance_vcpus {rr}")

            #time reserved for use by the software ; e.g : if the software is running for whole 5 minutes, then tr = 5
            tr = resource_observations.get("tr", None) 
            
            # Calculate the E-CPU, E-Mem, and E-GPU metrics
            ecpu = self.calculate_ecpu(cpu_util, timespan=timespan, tdp=tdp, core_count=rr, tr=tr)
            emem = self.calculate_emem(mem_util) #memory model uses only the average memory utilization in GB (calculated for the given timespan))
            egpu = self.calculate_egpu(gpu_util, timespan=timespan, tdp=tdp, gpu_count=rr)

            # Calculate the M and SCI metrics
            i = float(CI)


            total_vcpus = static_params.get(resource_name, {}).get("total_vcpus", 16) or 16
            te = static_params.get(resource_name, {}).get("te", 1200) or 1200

            m = self.calculate_m(timespan=timespan, rr=rr, total_vcpus=total_vcpus, te=te, tr=tr)

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

            resource_metadata = metadata.get(resource_name, {}) 
            metric_obj = SCIImpactMetricsInterface(metrics=impact_metrics, metadata=resource_metadata, observations=resource_observations, components_list=[], static_params=static_params.get(resource_name, {}))
            print(metric_obj)
            resource_metrics[resource_name] = metric_obj

            # Remove any metrics with None values
            #resource_metrics[resource_name] = {k: v for k, v in resource_metrics[resource_name].items() if v is not None}

        # Create an instance of the ImpactMetricInterface with the calculated metrics

        print("coucou")
        #metrics.metrics = resource_metrics


        return resource_metrics