import csv
import sys
import json
from typing import Dict, List
from prometheus_client import start_http_server, Gauge, REGISTRY

sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.ief.core import ImpactNodeInterface, SCIImpactMetricsInterface


class MetricsExporter:
    # Define the Gauge instances in the __init__ method
    e_cpu_gauge = Gauge("E_CPU", "Energy consumed by CPU", ["name", "model_name", "type"])
    e_mem_gauge = Gauge("E_MEM", "Energy consumed by memory", ["name", "model_name", "type"])
    e_gpu_gauge = Gauge("E_GPU", "Energy consumed by GPU", ["name", "model_name", "type"])
    e_gauge = Gauge("E", "Total energy consumed", ["name", "model_name", "type"])
    i_gauge = Gauge("I", "Carbon intensity", ["name", "model_name", "type"])
    m_gauge = Gauge("M", "Fixed metric value", ["name", "model_name", "type"])
    sci_gauge = Gauge("SCI", "SCI metric", ["name", "model_name", "type"])
   
    def __init__(self, data: Dict[str, SCIImpactMetricsInterface]):
        self.data = data
   

    def add_data(self, key, value):
        self.data[key] = value

    def to_csv(self, file_path):
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "model_name", "E_CPU", "E_MEM", "E_GPU", "E", "I", "M", "SCI"])
            for key, value in self.data.items():
                writer.writerow([value.name, value.model, value.E_CPU, value.E_MEM, value.E_GPU, value.E, value.I, value.M, value.SCI])

    def to_json(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.data, f, default=lambda x: x.__dict__)

    @staticmethod
    def start_http_server(port):
        start_http_server(port)

    def to_prometheus(self):
        for key, value in self.data.items():
            print(value.name, value.model, value.type)
            # Set the value of each Gauge to the corresponding value in the data dictionary
            self.e_cpu_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E_CPU)
            self.e_mem_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E_MEM)
            self.e_gpu_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E_GPU)
            self.e_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E)
            self.i_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.I)
            self.m_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.M)
            self.sci_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.SCI)
