import csv
import sys
import json
from typing import Dict, List
from prometheus_client import start_http_server, Gauge, REGISTRY

sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.ief.core import ImpactNodeInterface, SCIImpactMetricsInterface


# class MetricsExporter2:
#     # Define the Gauge instances in the __init__ method
#     e_cpu_gauge = Gauge("E_CPU", "Energy consumed by CPU", ["name", "model_name", "type"])
#     e_mem_gauge = Gauge("E_MEM", "Energy consumed by memory", ["name", "model_name", "type"])
#     e_gpu_gauge = Gauge("E_GPU", "Energy consumed by GPU", ["name", "model_name", "type"])
#     e_gauge = Gauge("E", "Total energy consumed", ["name", "model_name", "type"])
#     i_gauge = Gauge("I", "Carbon intensity", ["name", "model_name", "type"])
#     m_gauge = Gauge("M", "Fixed metric value", ["name", "model_name", "type"])
#     sci_gauge = Gauge("SCI", "SCI metric", ["name", "model_name", "type"])
   
#     def __init__(self, data: Dict[str, SCIImpactMetricsInterface]):
#         self.data = data
   

#     def add_data(self, key, value):
#         self.data[key] = value

#     def to_csv(self, file_path):
#         with open(file_path, 'w', newline='') as f:
#             writer = csv.writer(f)
#             writer.writerow(["name", "model_name", "E_CPU", "E_MEM", "E_GPU", "E", "I", "M", "SCI"])
#             for key, value in self.data.items():
#                 writer.writerow([value.name, value.model, value.E_CPU, value.E_MEM, value.E_GPU, value.E, value.I, value.M, value.SCI])

#     def to_json(self, file_path):
#         with open(file_path, 'w') as f:
#             json.dump(self.data, f, default=lambda x: x.__dict__)

#     @staticmethod
#     def start_http_server(port):
#         start_http_server(port)

#     def to_prometheus(self):
#         for key, value in self.data.items():
#             print(value.name, value.model, value.type)
#             # Set the value of each Gauge to the corresponding value in the data dictionary
#             self.e_cpu_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E_CPU)
#             self.e_mem_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E_MEM)
#             self.e_gpu_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E_GPU)
#             self.e_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.E)
#             self.i_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.I)
#             self.m_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.M)
#             self.sci_gauge.labels(name=value.name, model_name=value.model, type=value.type).set(value.SCI)


class MetricsExporter:
    def __init__(self, data: Dict[str, SCIImpactMetricsInterface] = {}, labels: List[str] = [], prefix: str = ""):
        self.data = data
        self.labels = labels
        self.prefix = prefix
        self.e_cpu_gauge = Gauge(f"{prefix}_E_CPU", "Energy consumed by CPU", self.labels)
        self.e_mem_gauge = Gauge(f"{prefix}_E_MEM", "Energy consumed by memory", self.labels)
        self.e_gpu_gauge = Gauge(f"{prefix}_E_GPU", "Energy consumed by GPU", self.labels)
        self.e_gauge = Gauge(f"{prefix}_E", "Total energy consumed", self.labels)
        self.i_gauge = Gauge(f"{prefix}_I", "Carbon intensity", self.labels)
        self.m_gauge = Gauge(f"{prefix}_M", "Fixed metric value", self.labels)
        self.sci_gauge = Gauge(f"{prefix}_SCI", "SCI metric", self.labels)

    def set_data(self, data = {}):
        self.data = data

    def to_csv(self, file_path):
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.labels + ["E_CPU", "E_MEM", "E_GPU", "E", "I", "M", "SCI"])
            for key, value in self.data.items():
                writer.writerow([getattr(value, label) for label in self.labels] + [value.E_CPU, value.E_MEM, value.E_GPU, value.E, value.I, value.M, value.SCI])

    def to_json(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.data, f, default=lambda x: x.__dict__)

    @staticmethod
    def start_http_server(port):
        start_http_server(port)

    def to_prometheus(self):
        for key, value in self.data.items():
            # Set the value of each Gauge to the corresponding value in the data dictionary
            self.e_cpu_gauge.labels(**self._get_labels(value)).set(value.E_CPU)
            self.e_mem_gauge.labels(**self._get_labels(value)).set(value.E_MEM)
            self.e_gpu_gauge.labels(**self._get_labels(value)).set(value.E_GPU)
            self.e_gauge.labels(**self._get_labels(value)).set(value.E)
            self.i_gauge.labels(**self._get_labels(value)).set(value.I)
            self.m_gauge.labels(**self._get_labels(value)).set(value.M)
            self.sci_gauge.labels(**self._get_labels(value)).set(value.SCI)

    def _get_labels(self, value):
        return {label: getattr(value, label) for label in self.labels}


class AzureVMExporter(MetricsExporter):
    def __init__(self, data: Dict[str, SCIImpactMetricsInterface]):
        super().__init__(data, ["name", "model", "type", "vm_size", "os_type"], "azure_vm")

class AKSNodeExporter(MetricsExporter):
    def __init__(self, data: Dict[str, SCIImpactMetricsInterface]):
        super().__init__(data, ["name", "model", "type"], "aks_node")

class AKSPodExporter(MetricsExporter):
    def __init__(self, data: Dict[str, SCIImpactMetricsInterface]):
        super().__init__(data, ["name", "model", "controller", "controllerKind", "namespace", "node"], "aks_pod")

    def set_data(self, data={}):
        super().set_data(data)
        new_data = {}
        for resource, impactdata in self.data.items():
            metadata = impactdata.metadata
            new_data[resource] = impactdata
            new_data[resource].metadata["controller"] = metadata.get("controller", "")
            new_data[resource].metadata["controllerKind"] = metadata.get("controllerKind", "")
            new_data[resource].metadata["namespace"] = metadata.get("namespace", "")
            new_data[resource].metadata["node"] = metadata.get("node", "")
        self.data = new_data


    def _get_labels(self, value):
        return {
            "name": value.name,
            "model": value.model,
            "controller": value.metadata.get("controller", ""),
            "controllerKind": value.metadata.get("controllerKind", ""),
            "namespace": value.metadata.get("namespace", ""),
            "node": value.metadata.get("node", "")
        }