class KubernetesMetadataProvider:
    def __init__(self, selector):
        self.selector = selector

    def get_metadata(self):
        # Your implementation of the get_metadata function here
        pass

    def get_usage_telemetry(self):
        # Your implementation of the get_usage_telemetry function here
        pass


class KubernetesSCIExporter:
    def __init__(self, metadata_provider):
        self.metadata_provider = metadata_provider

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

    def export_sci_metrics(self):
        metadata = self.metadata_provider.get_metadata()
        usage_telemetry = self.metadata_provider.get_usage_telemetry()
        # Your implementation of the export_sci_metrics function here
        pass