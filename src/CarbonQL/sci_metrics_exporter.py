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
        self.hostname = "toto"

        # Define the Prometheus metrics
        self.E = Gauge('E', 'Description of E', ['hostname'])
        self.M = Gauge('M', 'Description of M', ['hostname'])
        self.I = Gauge('I', 'Description of I', ['hostname'])
        self.SCI = Gauge('SCI', 'Description of SCI', ['hostname'])

        # Start the Prometheus HTTP server
        self.app = make_wsgi_app()
        self.port = port

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

    def start_http_server(self):
        start_http_server(int(self.port), addr='0.0.0.0')
        print(f'Serving Prometheus metrics on http://localhost:{self.port}/metrics')
