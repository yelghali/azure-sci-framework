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
from lib.ief.core import ImpactNodeInterface
from lib.models.computeserver_static_imp import ComputeServer_STATIC_IMP
from lib.MetricsExporter.exporter import MetricsExporter



class Component(BaseModel):
    auth_params: Dict[str, str]
    name: str
    type: str
    resource_selectors: Dict[str, str]
    metadata: Dict[str, str]

class MetricsRequest(BaseModel):
    app_name: str
    components: List[Component]
    interval: str
    timespan: str

app = FastAPI()

aggregation = MetricAggregationType.AVERAGE

@app.post("/metrics")
async def get_metrics(request: MetricsRequest = Body(...)):
    print(request)
    data = {}
    for component in request.components:
        print(component)
        # Create an instance of the appropriate subclass of ImpactNodeInterface
        if component.type == 'AzureVM':
            node = AzureVM(ComputeServer_STATIC_IMP(), None, component.auth_params, resource_selectors=component.resource_selectors, metadata=component.metadata)
            node.fetch_resources()
            # Fetch and calculate the carbon impact metrics for this component
            node.fetch_observations(aggregation=aggregation, interval="PT15M", timespan="PT1H")
            print(node.observations)
            toto = node.calculate()
            #metrics = node.run()
            metrics = toto
            data[component.name] = metrics
        elif component.type == 'AKSNode':
            #node = AKSNode(...)
            pass
        else:
            continue
    return data


def main():
    uvicorn.run(f"{__name__}:app", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()