from CarbonQL import CarbonQLComponent, CarbonIntensityProvider, NodeResourceProvider, NodeSCIModel, SCIMetricsExporter

import time

def app():

    WattTimeCarbonIntensityProvider = CarbonIntensityProvider(source='watttime')
    # Create an instance of the CarbonQLComponent class
    component = CarbonQLComponent(carbon_intensity_provider=WattTimeCarbonIntensityProvider, resource_provider_class=NodeResourceProvider, sci_model_class=NodeSCIModel, resource_label_selectors=['label1', 'label2'])
    
    print(component.resource_provider.get_metadata())
    print(component.resource_provider.get_usage_telemetry())
    print(component.get_sci_model())
    print(component.get_total_energy())
    print(component.get_embodied_emissions())
    print(component.get_sci_metrics())

    # Create an instance of the SCIMetricsExporter class (to export metrics to a Metrics Workspace such as Prometheus or Azure Monitor)
    exporter = SCIMetricsExporter(port=8000, carbonql_component=component)
    
    exporter.start_http_server()
    # Export the SCI metrics to Prometheus
    while True:
        exporter.export_sci_metrics()
        time.sleep(5)
    # Export the SCI metrics to Prometheus
    #exporter.export_sci_metrics()

if __name__ == '__main__':
    app()