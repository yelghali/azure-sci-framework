from lib.ief.core import ImpactModelPluginInterface, SCIImpactMetricsInterface
from typing import Dict, List


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

    def calculate_ecpu(self, cpu_util) -> float:
        if cpu_util is not None and 0 <= cpu_util <= 100:
            # Calculate the power consumed by the CPU using the power curve model
            pc = 0.7 * cpu_util + 0.3 * 205 # 205 W is the TDP of the processor

            # Calculate the energy consumed by the CPU over the past hour
            ecpu = pc * 3600 / 1000  # Convert from Ws to kWh

            return ecpu

        return 0

    def calculate_emem(self, mem_util) -> float:
        if mem_util is not None and 0 <= mem_util <= 100:
            # Calculate the power consumed by the memory using a linear model
            pm = 0.1 * mem_util + 2.5  # 2.5 W is the idle power consumption of the memory

            # Calculate the energy consumed by the memory over the past hour
            emem = pm * 3600 / 1000  # Convert from Ws to kWh

            return emem

        return 0

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