from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import List, Dict

import uvicorn


# sample instanciation with prints of AzureVM class
import sys
from azure.mgmt.monitor.models import MetricAggregationType
import time

sys.path.append('./lib')
from lib.components.azure_vm import AzureVM
from lib.components.azure_aks_node import AKSNode
from lib.components.azure_aks_pod import AKSPod
from lib.ief.core import *
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.MetricsExporter.exporter import MetricsExporter



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

app = FastAPI()

aggregation = MetricAggregationType.AVERAGE

@app.post("/metrics")
async def get_metrics(request: AggregatedComponentRequest = Body(...)):
    print(request)
    data = {}
    components = []
    for component in request.components:
        print(component)
        # Create an instance of the appropriate subclass of ImpactNodeInterface
        if component.type == 'AzureVM':
            node = AzureVM(name = component.name, model=ComputeServer_STATIC_IMP(), carbon_intensity_provider=None, auth_object=component.auth_params, resource_selectors=component.resource_selectors, metadata=component.metadata, interval=request.interval, timespan=request.timespan)
            components.append(node)
        elif component.type == 'AKSNode':
            node = AKSNode(name = component.name, model = ComputeServer_STATIC_IMP(), carbon_intensity_provider=None, auth=component.auth_params, resource_selectors=component.resource_selectors, metadata=component.metadata, interval=request.interval, timespan=request.timespan)
            components.append(node)
        elif component.type == 'AKSPod':
            pod = AKSPod(name = component.name, model = ComputeServer_STATIC_IMP(),  carbon_intensity_provider=None, auth_object=component.auth_params, resource_selectors=component.resource_selectors, metadata=component.metadata, interval=request.interval, timespan=request.timespan)
            components.append(pod)
        else:
            continue

    # Create an instance of the AggregatedImpactNodesInterface class for the aggregated component
    aggregated_component = AggregatedImpactNodesInterface(
        name=request.app_name,
        components=components,
        timespan=request.timespan,
        interval=request.interval
    )

    # Calculate the metrics for the aggregated component and its child components
    metrics = aggregated_component.calculate()

    return metrics


def main():
    uvicorn.run(f"{__name__}:app", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()