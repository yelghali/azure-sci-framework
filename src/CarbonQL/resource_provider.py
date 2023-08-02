from kubernetes import client, config
import datetime
import json

class CarbonQLResourceProvider:
    def __init__(self, resource_label_selectors):
        self.resource_label_selectors = resource_label_selectors

    def get_metadata(self):
        # Your implementation of the get_metadata function here
        pass

    def get_usage_telemetry(self):
        # Your implementation of the get_usage_telemetry function here
        pass


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
