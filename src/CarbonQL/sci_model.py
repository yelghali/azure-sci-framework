from kubernetes import client, config
import datetime
import json

class CarbonQLSCIModel:
    def __init__(self):
        pass

    def calculate_cpu_energy(self, resource_info):
        # Your implementation of the calculate_cpu_energy function here
        pass

    def calculate_memory_energy(self, resource_info):
        # Your implementation of the calculate_memory_energy function here
        pass

    def calculate_total_energy(self, cpu_energy, memory_energy, embodied_emissions):
        # Your implementation of the calculate_total_energy function here
        pass

    def calculate_embodied_emissions(self, resource_info):
        # Your implementation of the calculate_embodied_emissions function here
        pass

    def calculate_sci(self, total_energy, embodied_emissions):
        # Your implementation of the calculate_sci function here
        pass




class NodeSCIModel(CarbonQLSCIModel):
    def __init__(self):
        super().__init__()

    def calculate_cpu_energy(self,resource_info):
        tdp = float(resource_info.get('cpu').rstrip('n'))
        cpu_usage_percentage = float(resource_info['cpu_percentage'])
        # Calculate the TDP coefficient based on the CPU utilization percentage
        if cpu_usage_percentage == 0:
            tdp_coefficient = 0.12
        elif cpu_usage_percentage == 100:
            tdp_coefficient = 1.02
        else:
            tdp_coefficient = 0.12 + (0.9 * (cpu_usage_percentage / 100))

        # Calculate the energy consumption based on the TDP and TDP coefficient
        energy_consumption = tdp * tdp_coefficient

        return energy_consumption

    def calculate_memory_energy(self,resource_info):
        memory_usage_percentage = float(resource_info['memory_percentage'])

        # Memory energy consumption in Joules per GB
        energy_per_gb = 0.0000001

        # Total memory capacity in GB
        total_memory_gb = 64

        # Memory usage in GB
        memory_usage_gb = (memory_usage_percentage / 100) * total_memory_gb

        # Energy consumption in Joules
        energy_consumption = memory_usage_gb * energy_per_gb

        return energy_consumption


    def calculate_embodied_emissions(self, resource_info):
        # TE: Embodied carbon estimates for the servers from the Cloud Carbon Footprint Coefficient Data Set
        te = 0.5  # kgCO2e/hour

        # TR: Time reserved for the hardware
        tr = 1  # hour

        # EL: Expected lifespan of the equipment
        el = 35040  # hours (4 years)

        # RR: Resources reserved for use by the software
        rr = 2  # vCPUs

        # TR: Total number of resources available
        total_vcpus = 16

        # Calculate M using the equation M = TE * (TR/EL) * (RR/TR)
        m = te * (tr / el) * (rr / total_vcpus)

        return m

    def calculate_sci_metrics(self):
        sci_metrics = {}
        return sci_metrics
