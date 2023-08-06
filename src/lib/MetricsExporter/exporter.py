import csv
import json
from typing import Dict, List
from prometheus_client import start_http_server, Gauge, REGISTRY

class MetricsExporter:
    def __init__(self, data: Dict[str, object]):
        self.data = data

    def to_csv(self, file_path: str):
        with open(file_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=self.data.keys())
            writer.writeheader()
            writer.writerow(self.data)

    def to_json(self, file_path: str):
        with open(file_path, 'w') as f:
            json.dump(self.data, f)

    @staticmethod
    def start_http_server(port: int):
        start_http_server(port)
   

    def to_prometheus(self):
        gauges = {}
        for key, value in self.data.items():
            # Unregister any existing collector with the same name
            if key in REGISTRY._names_to_collectors:
                REGISTRY.unregister(REGISTRY._names_to_collectors[key])
            # Register a new collector
            gauges[key] = Gauge(key, documentation=key)
            gauges[key].set(value)
