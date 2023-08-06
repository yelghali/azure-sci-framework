from prometheus_client import Gauge, start_http_server
from kubernetes import client, config
import datetime
import json

from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.exposition import make_wsgi_app
from wsgiref.simple_server import make_server
from prometheus_client import start_wsgi_server

class SCIMetricsExporter:
    def __init__(self, carbonql_component, port=8000):
        self.carbonql_component = carbonql_component
        self.resource_metadata = self.carbonql_component.resource_provider.get_metadata()
        self.hostname = "toto"

        # Define the Prometheus metrics
        self.E = Gauge('E', 'Description of E', ['node_name', 'cluster_name'])
        print(self.resource_metadata)
        self.M = Gauge('M', 'Description of M', ['node_name', 'cluster_name'])
        self.I = Gauge('I', 'Description of I', ['node_name', 'cluster_name'])
        self.SCI = Gauge('SCI', 'Description of SCI', ['node_name', 'cluster_name'])

        # Start the Prometheus HTTP server
        self.app = make_wsgi_app()
        self.port = port

    def export_sci_metrics(self):
        # Get the SCI metrics from the component
        nodes_sci_metrics = self.carbonql_component.get_sci_metrics()
        print(nodes_sci_metrics)

        for node_name, sci_metrics in nodes_sci_metrics.items():
            # Set the values for each metric with the hostname label
            self.E.labels(node_name=node_name, cluster_name='sus-aks-lab').set(sci_metrics['E'])
            self.M.labels(node_name=node_name, cluster_name='sus-aks-lab').set(sci_metrics['M'])
            self.I.labels(node_name=node_name, cluster_name='sus-aks-lab').set(sci_metrics['I'])
            self.SCI.labels(node_name=node_name, cluster_name='sus-aks-lab').set(sci_metrics['SCI'])

    def start_http_server(self):
        start_http_server(int(self.port), addr='0.0.0.0')
        print(f'Serving Prometheus metrics on http://localhost:{self.port}/metrics')
