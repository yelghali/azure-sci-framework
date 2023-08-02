
class CarbonQLComponent:
    def __init__(self, carbon_intensity_provider, resource_provider_class, sci_model_class, resource_label_selectors):
        self.carbon_intensity_provider = carbon_intensity_provider
        self.resource_label_selectors = resource_label_selectors
        self.resource_provider = resource_provider_class(resource_label_selectors)
        self.sci_model = sci_model_class()

    def get_resource_metadata(self):
        return self.resource_provider.get_metadata()

    def get_resource_observations(self):
        return self.resource_provider.get_usage_telemetry()
    
    def get_region_carbon_intensity(self):
        return self.carbon_intensity_provider.get_carbon_intensity()
    
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
