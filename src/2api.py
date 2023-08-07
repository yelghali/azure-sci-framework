from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import List, Dict

import uvicorn

# sample instanciation with prints of AzureVM class
import sys
from azure.mgmt.monitor.models import MetricAggregationType
import time


class ComponentRequest(BaseModel):
    name: str
    auth_params: Dict[str, str]
    type: str
    resource_selectors: Dict[str, str]
    metadata: Dict[str, str]

class AggregatedComponentRequest(BaseModel):
    app_name: str
    components: List[ComponentRequest]
    interval: str
    timespan: str


sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.components.azure_aks_node import AKSNode
from lib.ief.core import *
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.MetricsExporter.exporter import MetricsExporter

app = FastAPI()

aggregation = MetricAggregationType.AVERAGE

@app.post("/metrics/azurevm")
async def get_azure_vm_metrics(request: ComponentRequest = Body(...)):
    # Create an instance of the AzureVM class
    node = AzureVM(ComputeServer_STATIC_IMP(), None, request.auth_params, resource_selectors=request.resource_selectors, metadata=request.metadata)

    # Calculate the metrics for the Azure VM
    metrics = node.calculate()

    return metrics

@app.post("/metrics/aksnode")
async def get_aks_node_metrics(request: ComponentRequest = Body(...)):
    # Create an instance of the AKSNode class
    node = AKSNode(ComputeServer_STATIC_IMP(), None, request.auth_params, resource_selectors=request.resource_selectors, metadata=request.metadata)

    # Calculate the metrics for the AKS node
    metrics = node.calculate()

    return metrics

@app.post("/metrics")
async def get_metrics(request: AggregatedComponentRequest = Body(...)):
    data = {}
    components = []
    for component in request.components:
        # Create an instance of the appropriate subclass of ImpactNodeInterface
        if component.type == 'AzureVM':
            node = AzureVM(ComputeServer_STATIC_IMP(), None, component.auth_params, resource_selectors=component.resource_selectors, metadata=component.metadata)
            components.append(node)

        elif component.type == 'AKSNode':
            node = AKSNode(ComputeServer_STATIC_IMP(), None, component.auth_params, resource_selectors=component.resource_selectors, metadata=component.metadata)
            components.append(node)

        else:
            continue

    # Create an instance of the AggregatedImpactNodesInterface class for the aggregated component
    aggregated_component = AggregatedImpactNodesInterface(
        name=request.app_name,
        components=components
    )

    # Calculate the metrics for the aggregated component and its child components
    metrics = aggregated_component.calculate()

    return metrics




def main():
    uvicorn.run(f"{__name__}:app", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()