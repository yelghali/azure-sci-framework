from prometheus_client import Gauge, start_http_server
from kubernetes import client, config
import datetime
import json

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
