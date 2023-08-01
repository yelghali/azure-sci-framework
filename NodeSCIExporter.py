from kubernetes import client, config
import datetime
import json

# Load the Kubernetes configuration from the default location
config.load_kube_config()


class KubernetesSCIExporter:
    def __init__(self, selector):
        self.metadata = self.get_metadata(selector)

    def get_metadata(self, selector):
        # Your implementation of the get_metadata function here
        pass

    def get_usage_telemetry(self, selector):
        # Your implementation of the get_usage_telemetry function here
        pass

    def calculate_cpu_energy(self, usage_percentage, tdp):
        # Your implementation of the calculate_cpu_energy function here
        pass

    def calculate_memory_energy(self, usage_percentage, memory):
        # Your implementation of the calculate_memory_energy function here
        pass

    def calculate_total_energy(self, cpu_energy, memory_energy, embodied_emissions):
        # Your implementation of the calculate_total_energy function here
        pass

    def calculate_embodied_emissions(self, sku):
        # Your implementation of the calculate_embodied_emissions function here
        pass

    def calculate_sci(self, total_energy, embodied_emissions):
        # Your implementation of the calculate_sci function here
        pass



class NodeSCIExporter(KubernetesSCIExporter):
    def __init__(self, selector):
        super().__init__(selector)

    def get_metadata(self, selector="all"):
        # Create a Kubernetes API client for the CoreV1Api
        api_client = client.CoreV1Api()

        # Get the name of the current context and cluster from the Kubernetes configuration file
        current_context = config.list_kube_config_contexts()[1]
        current_cluster = current_context['context']['cluster']

        # Query the Kubernetes API server for the list of nodes in the cluster
        nodes = api_client.list_node().items

        # Get the names and metadata of all nodes in the cluster
        node_metadata = []
        for node in nodes:
            node_name = node.metadata.name
            node_labels = node.metadata.labels
            node_pool_name = node_labels.get('kubernetes.azure.com/agentpool', 'unknown')
            cluster_region = node_labels.get('failure-domain.beta.kubernetes.io/region', 'unknown')
            node_zone = node_labels.get('failure-domain.beta.kubernetes.io/zone', 'unknown')
            node_arch = node_labels.get('beta.kubernetes.io/arch', 'unknown')
            node_os = node_labels.get('kubernetes.azure.com/os-sku', 'unknown')
            node_mode = node_labels.get('kubernetes.azure.com/mode', 'unknown')
            node_sku = node_labels.get('beta.kubernetes.io/instance-type', 'unknown')
            node_metadata.append({
                'node_name': node_name,
                'cluster_name': current_cluster,
                'node_pool_name': node_pool_name,
                'cluster_region': cluster_region,
                'node_zone': node_zone,
                'node_arch': node_arch,
                'node_os': node_os,
                'node_mode': node_mode,
                'node_sku': node_sku
            })

        return node_metadata

    def get_usage_telemetry(self, selector="all"):

        # Create an instance of the API class
        api_instance = client.CustomObjectsApi()
        core_api_instance = client.CoreV1Api()

        # Get the node metrics
        node_metrics = api_instance.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")

        # Get the node information
        nodes = core_api_instance.list_node()

        # Create a dictionary to store the node usage telemetry
        node_usage_telemetry = {}

        # Iterate over the nodes and get their usage telemetry
        for item in node_metrics['items']:
            node_name = item['metadata']['name']
            cpu_usage_str = item['usage']['cpu']
            memory_usage_str = item['usage']['memory']

            # Find the corresponding node in the node information
            node_info = next(node for node in nodes.items if node.metadata.name == node_name)

            # Get the allocatable resources for the node
            allocatable_cpu_str = node_info.status.allocatable.get('cpu')
            allocatable_memory_str = node_info.status.allocatable.get('memory')

            # Check that the allocatable CPU and memory values are valid
            if not allocatable_cpu_str:
                raise ValueError(f"Invalid allocatable CPU value for node {node_name}")
            if not allocatable_memory_str:
                raise ValueError(f"Invalid allocatable memory value for node {node_name}")

            # Convert CPU and memory usage to floats
            cpu_usage = float(cpu_usage_str.rstrip('n')) / 1000
            memory_usage = float(memory_usage_str.rstrip('Ki')) / (1024 ** 2)

            # Convert allocatable CPU and memory to floats
            allocatable_cpu = float(allocatable_cpu_str.rstrip('m')) / 1000
            allocatable_memory = float(allocatable_memory_str.rstrip('Ki'))

            # Calculate the percentage utilization of CPU and memory
            cpu_usage_percentage = (cpu_usage / allocatable_cpu) * 100
            memory_usage_percentage = (memory_usage / allocatable_memory) * 100

            # Calculate the CPU power consumption based on the TDP and CPU utilization percentage
            tdp = node_info.status.capacity.get('cpu').rstrip('m')
            cpu_energy = self.calculate_cpu_energy(cpu_usage_percentage, float(tdp))

            # Store the usage telemetry in the dictionary
            node_usage_telemetry[node_name] = {
                'cpu': cpu_usage_str,
                'cpu_percentage': cpu_usage_percentage,
                'cpu_energy': cpu_energy,
                'memory': memory_usage_str,
                'memory_percentage': memory_usage_percentage
            }
        return node_usage_telemetry

    def calculate_cpu_energy(self,cpu_usage_percentage, tdp):
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

    def calculate_memory_energy(self,memory_usage_percentage):
        # Memory energy consumption in Joules per GB
        energy_per_gb = 0.0000001

        # Total memory capacity in GB
        total_memory_gb = 64

        # Memory usage in GB
        memory_usage_gb = (memory_usage_percentage / 100) * total_memory_gb

        # Energy consumption in Joules
        energy_consumption = memory_usage_gb * energy_per_gb

        return energy_consumption

    def calculate_total_energy(self):
        # Get the usage telemetry for all nodes
        node_usage_telemetry = self.get_usage_telemetry()

        # Calculate the CPU energy consumption for each node
        for node_name, node_info in node_usage_telemetry.items():
            tdp = node_info.get('cpu').rstrip('n')
            cpu_energy = self.calculate_cpu_energy(node_info['cpu_percentage'], float(tdp))
            node_info['cpu_energy'] = cpu_energy

        # Calculate the memory energy consumption for each node
            memory_energy = self.calculate_memory_energy(node_info['memory_percentage'])
            node_info['memory_energy'] = memory_energy

        # Generate a dictionary containing the node name, node CPU energy, and node memory energy
        node_energy = {}
        node_energy[node_name] = {
                'cpu_energy': node_info['cpu_energy'],
                'memory_energy': node_info['memory_energy'],
                'total_energy': node_info['cpu_energy'] + node_info['memory_energy']
            }

        return node_energy

    def calculate_embodied_emissions_m(self, node_sku):
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

    def export_sci_metrics(self):
        node_metadata = self.get_metadata()
        print(node_metadata)
        print("######\n")
        #forecast_i = get_forecast_i()
        node_usage_telemetry = self.get_usage_telemetry()
        print(node_usage_telemetry)
        print("######\n")

        node_energy = self.calculate_total_energy()
        print(node_energy)
        print("######\n")

        sci_metrics = self.calculate_sci_metrics()
        print(sci_metrics)

        # TODO: Implement this function to calculate the SCI metrics for each node
        return None
    

if __name__ == '__main__':
    selector = "all"  # Replace with your desired selector
    exporter = NodeSCIExporter(selector)
    sci= exporter.export_sci_metrics()
    print(exporter.get_metadata())
    print(sci)