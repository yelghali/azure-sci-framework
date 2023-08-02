from kubernetes import client, config
import datetime
import json




#########################

class CarbonQLResourceProvider:
    def __init__(self, resource_label_selectors):
        self.resource_label_selectors = resource_label_selectors

    def get_metadata(self):
        # Your implementation of the get_metadata function here
        pass

    def get_usage_telemetry(self):
        # Your implementation of the get_usage_telemetry function here
        pass


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

    ######################

class NodeResourceProvider(CarbonQLResourceProvider):
    def __init__(self, resource_label_selectors):
        # Load the Kubernetes configuration from the default location
        config.load_kube_config()
        super().__init__(resource_label_selectors)

    def get_metadata(self, resource_label_selectors="all"):
        # Create a Kubernetes API client for the CoreV1Api
        api_client = client.CoreV1Api()

        # Get the name of the current context and cluster from the Kubernetes configuration file
        current_context = config.list_kube_config_contexts()[1]
        current_cluster = current_context['context']['cluster']

        # Query the Kubernetes API server for the list of nodes in the cluster
        nodes = api_client.list_node().items

        # Get the names and metadata of all nodes in the cluster
        node_metadata = {}
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
            node_metadata[node_name] =  {
                'node_name': node_name,
                'cluster_name': current_cluster,
                'node_pool_name': node_pool_name,
                'cluster_region': cluster_region,
                'node_zone': node_zone,
                'node_arch': node_arch,
                'node_os': node_os,
                'node_mode': node_mode,
                'node_sku': node_sku
            }

        return node_metadata

    def get_usage_telemetry(self, resource_label_selectors="all"):

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

            # Store the usage telemetry in the dictionary
            node_usage_telemetry[node_name] = {
                'cpu': cpu_usage_str,
                'cpu_percentage': cpu_usage_percentage,
                'memory': memory_usage_str,
                'memory_percentage': memory_usage_percentage
            }
        return node_usage_telemetry


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
  




    # You can add additional methods or override methods here if needed




    # You can add additional methods or override methods here if neededs


    ############


class CarbonQLComponent:
    def __init__(self, resource_provider_class, sci_model_class, resource_label_selectors):
        self.resource_label_selectors = resource_label_selectors
        self.resource_provider = resource_provider_class(resource_label_selectors)
        self.sci_model = sci_model_class()

    def get_resource_metadata(self):
        return self.resource_provider.get_metadata()

    def get_resource_observations(self):
        return self.resource_provider.get_usage_telemetry()
    
    def get_region_carbon_intensity(self):
        # return self.sci_model.get_region_carbon_intensity()
        return 100
    
    def get_sci_model(self):
        return self.sci_model
    
    def get_total_energy(self):
        # Get the usage telemetry for all nodes
        resource_usage_telemetry = self.resource_provider.get_usage_telemetry()

        # Calculate the CPU energy consumption for each node
        for resource_name, resource_info in resource_usage_telemetry.items():
            cpu_energy = self.sci_model.calculate_cpu_energy(resource_info)
            resource_info['cpu_energy'] = cpu_energy

        # Calculate the memory energy consumption for each node
            memory_energy = self.sci_model.calculate_memory_energy(resource_info)
            resource_info['memory_energy'] = memory_energy

        # Generate a dictionary containing the node name, node CPU energy, and node memory energy
        resource_energy = {}
        resource_energy[resource_name] = {
                'cpu_energy': resource_info['cpu_energy'],
                'memory_energy': resource_info['memory_energy'],
                'total_energy': resource_info['cpu_energy'] + resource_info['memory_energy']
            }

        return resource_energy

    def get_embodied_emissions(self):
        # Get the usage telemetry for all nodes
        resource_usage_telemetry = self.resource_provider.get_usage_telemetry()

        # Calculate the CPU energy consumption for each node
        for resource_name, resource_info in resource_usage_telemetry.items():
            embodied_emissions = self.sci_model.calculate_embodied_emissions(resource_info)
            resource_info['embodied_emissions'] = embodied_emissions

 
        # Generate a dictionary containing the node name, node CPU energy, and node memory energy
        resource_em = {}
        resource_em[resource_name] = {
                'embodied_emissions': resource_info['embodied_emissions']
            }

        return resource_em
    
    def export_sci_metrics(self):
        metadata = self.resource_provider.get_metadata()
        usage_telemetry = self.resource_provider.get_usage_telemetry()
        print(usage_telemetry)
        print("######\n")



        sci_metrics = self.sci_model.calculate_sci_metrics()
        print(sci_metrics)

        # TODO: Implement this function to calculate the SCI metrics for each node
        return None
       
    def get_sci_metrics(self):
        node_energy = self.get_total_energy()
        node_embodied_emissions = self.get_embodied_emissions()
        region_carbon_intensity = self.get_region_carbon_intensity()

        # Merge the dictionaries by node name
        nodes = {}
        for d in [node_energy, node_embodied_emissions]:
            for k, v in d.items():
                nodes.setdefault(k, {}).update(v)

        # Calculate the SCI metrics for each node
        for node_name, node_data in nodes.items():
            E = node_data["total_energy"]
            I = region_carbon_intensity
            M = node_data["embodied_emissions"]
            SCI = (E * I) + M
            nodes[node_name]["SCI"] = SCI
            nodes[node_name]["I"] = I
            nodes[node_name]["E"] = E
            nodes[node_name]["M"] = M

        return nodes

    def get_ghg_metrics(self):
        pass

class CarbonQLKubernetesComponent(CarbonQLComponent):
    def __init__(self, resource_provider_class, sci_model_class, resource_label_selectors):
        super().__init__(resource_provider_class, sci_model_class, resource_label_selectors)

class CarbonQLNodeComponent(CarbonQLComponent):
    def __init__(self, resource_provider_class, sci_model_class, resource_label_selectors):
        super().__init__(resource_provider_class, sci_model_class, resource_label_selectors)

    ################


from prometheus_client import Gauge, start_http_server

class SCIMetricsExporter:
    def __init__(self, hostname, port, carbonql_component):
        self.hostname = hostname
        self.port = port
        self.carbonql_component = carbonql_component

        # Create a Gauge for each custom metric with a label for the hostname
        self.E = Gauge('E', 'Description of E', ['hostname'])
        self.M = Gauge('M', 'Description of M', ['hostname'])
        self.I = Gauge('I', 'Description of I', ['hostname'])
        self.SCI = Gauge('SCI', 'Description of SCI', ['hostname'])

        # Start the Prometheus HTTP server
        start_http_server(port)

    def export_sci_metrics(self):
        # Get the SCI metrics from the component
        nodes_sci_metrics = self.carbonql_component.get_sci_metrics()
        print(nodes_sci_metrics)

        for node_name, sci_metrics in nodes_sci_metrics.items():
            # Set the values for each metric with the hostname label
            self.E.labels(hostname=self.hostname).set(sci_metrics['E'])
            self.M.labels(hostname=self.hostname).set(sci_metrics['M'])
            self.I.labels(hostname=self.hostname).set(sci_metrics['I'])
            self.SCI.labels(hostname=self.hostname).set(sci_metrics['SCI'])


#####################

import time

def main():
    #metadata_provider = NodeResourceProvider(resource_label_selectors="all")
    #print(metadata_provider.get_metadata())
    #print(metadata_provider.get_usage_telemetry())
    #model = NodeSCIModel(metadata_provider)

    toto = CarbonQLNodeComponent(resource_provider_class=NodeResourceProvider, sci_model_class=NodeSCIModel, resource_label_selectors="all")
    print(toto.get_resource_metadata())
    print(toto.get_resource_observations())
    print(toto.get_sci_model())
    print(toto.get_sci_metrics())

    sci_metrics_exporter = SCIMetricsExporter(hostname="localhost", port=8000, carbonql_component=toto)
    while True:
        sci_metrics_exporter.export_sci_metrics()
        time.sleep(2)

if __name__ == "__main__":
    main()