from CarbonQL import CarbonQLComponent, NodeResourceProvider, NodeSCIModel, SCIMetricsExporter

def app():
    # Create an instance of the CarbonQLComponent class
    component = CarbonQLComponent(NodeResourceProvider, NodeSCIModel, ['label1', 'label2'])

    # Create an instance of the SCIMetricsExporter class
    exporter = SCIMetricsExporter('node2', 8081, component)

    # Export the SCI metrics to Prometheus
    exporter.export_sci_metrics()

if __name__ == '__main__':
    app()