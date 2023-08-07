from abc import ABC, abstractmethod
from typing import Dict, List
from pydantic import BaseModel
from azure.mgmt.monitor.models import MetricAggregationType

class AuthParams(ABC):
    @abstractmethod
    def get_credential(self) -> Dict[str, str]:
        pass


class SCIImpactMetricsInterface(BaseModel):
    name: str = "Name of the measured ImpactNode resource"
    unit: str = "severalUnits"
    type: str = "impactnode"
    model: str = "SCI Impact Model"
    description: str = "Description of SCI Impact Metrics"
    E_CPU: float
    E_MEM: float
    E_GPU: float
    E: float
    I: float
    M: float
    SCI: float

    metadata: Dict[str, str] = {}
    observations: Dict[str, object] = {}
    components: List[Dict[str,'SCIImpactMetricsInterface']] = []

    def __init__(self, metrics: Dict[str, float], metadata: Dict[str, str] = None, observations: Dict[str, object] = None, components_list: List['SCIImpactMetricsInterface'] = []):
        

        
        super().__init__(
            type=metrics.get('type'),
            name=metrics.get('name'),
            model=metrics.get('model'),
            E_CPU=metrics.get('E_CPU'),
            E_MEM=metrics.get('E_MEM'),
            E_GPU=metrics.get('E_GPU'),
            E=metrics.get('E'),
            I=metrics.get('I'),
            M=metrics.get('M'),
            SCI=metrics.get('SCI'),
            metadata=metadata,
            observations=observations,
            components=components_list
            )
        # we want only the SCIMetricInterface



class ImpactModelPluginInterface(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def model_identifier(self) -> str:
        pass

    @abstractmethod
    async def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactModelPluginInterface':
        pass

    @abstractmethod
    def authenticate(self, auth_params: Dict[str, object]) -> None:
        pass

    @abstractmethod
    def calculate(self, observations: Dict[str, object] = None, carbon_intensity : float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        pass


class CarbonIntensityPluginInterface(ABC):
    @abstractmethod
    def auth(self, auth_params: Dict[str, object]) -> None:
        pass

    @abstractmethod
    def configure(self, params: Dict[str, object]) -> None:
        pass

    @abstractmethod
    def get_current_carbon_intensity(self) -> float:
        pass

class ImpactMetricInterface(ABC):
    def __init__(self, name: str, description: str, unit: str, metadata: Dict[str, object]):
        self.name = name
        self.description = description
        self.unit = unit
        self.metadata = {}


aggregation = MetricAggregationType.AVERAGE

class ImpactNodeInterface(ABC):
    def __init__(self, model: ImpactModelPluginInterface = None, carbon_intensity_provider: CarbonIntensityPluginInterface = None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {}):
        self.type = "impactnode"
        self.name = "Undefined"
        self.inner_model = model
        self.carbon_intensity_provider = carbon_intensity_provider
        self.auth_object = auth_object
        self.resource_selectors = resource_selectors
        self.metadata = metadata
        self.resources = None
        self.observations = None

    def run(self) -> Dict[str, object]:
        self.authenticate(self.auth_object.get_auth_params())
        self.resources = self.fetch_resources()
        self.static_params = self.lookup_static_params()
        self.configure(self.name, self.static_params)
        self.observations = self.fetch_observation()
        return self.calculate(self.observations)

    @abstractmethod
    def authenticate(self, auth_params: Dict[str, object]) -> None:
        pass

    @abstractmethod    
    def fetch_resources(self) -> Dict[str, object]:
        #using label selectors, fetch resources from cloud provider
        pass

    @abstractmethod
    def fetch_observations(self) -> Dict[str, object]:
        #using label selectors, fetch observation from cloud provider
        pass

    @abstractmethod
    def lookup_static_params(self) -> Dict[str, object]:
        #lookup the static params for the model, corresponding to the fetched resources
        pass

    def calculate(self, carbon_intensity : float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        self.fetch_resources()


        self.fetch_observations(aggregation = None, carbon_intensity=100, interval="PT15M", timespan="PT1H")
        return self.inner_model.calculate(self.observations, carbon_intensity=carbon_intensity)

    def model_identifier(self) -> str:
        return self.inner_model.model_identifier()

    def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactNodeInterface':
        return self.inner_model.configure(name, static_params)



class AggregatedImpactNodesInterface(ABC):
    def __init__(self, name, components : List[ImpactNodeInterface], carbon_intensity_provider: CarbonIntensityPluginInterface = None, type=None, model=None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {} ):
        self.components = components  
        self.resource_selectors = resource_selectors
        self.metadata = metadata
        self.inner_model = "sumofcomponents"
        self.type = type if type is not None else "aggregatedimpactnode"
        self.name = name if name is not None else "undefined"
        self.carbon_intensity_provider = carbon_intensity_provider
        self.auth_object = auth_object


    def authenticate(self, auth_params: Dict[str, object]) -> None:
        pass

   
    def fetch_resources(self) -> Dict[str, object]:
        #using label selectors, fetch resources from cloud provider
        pass

    def fetch_observations(self) -> Dict[str, object]:
        #using label selectors, fetch observation from cloud provider
        pass

    def lookup_static_params(self) -> Dict[str, object]:
        #lookup the static params for the model, corresponding to the fetched resources
        pass

    def calculate(self, carbon_intensity: float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        # Calculate the metrics for each child component and sum their metrics
        resource_metrics = {}
        metrics_list = []
        node_metrics = []
        for component in self.components:
            print (component)
            component.fetch_resources()
            component.fetch_observations(aggregation, interval="PT15M", timespan="PT1H")
            impact_metrics = component.calculate(carbon_intensity=carbon_intensity)
            node_metrics.append(impact_metrics)
            for node_name, node_impact_metric in impact_metrics.items():
            # store the component in the dict
                metrics_list.append(node_impact_metric)

        print(metrics_list)
        # Calculate the total metrics for the aggregated component
        E_CPU = sum(component.E_CPU for component in metrics_list)
        E_MEM = sum(component.E_MEM for component in metrics_list)
        E_GPU = sum(component.E_GPU for component in metrics_list)
        E = sum(component.E for component in metrics_list)
        I = carbon_intensity
        M = sum(component.M for component in metrics_list)
        SCI = sum(component.SCI for component in metrics_list)

        # Create a new SCIImpactMetricsInterface instance with the calculated metrics
        aggregated_metrics = {
            'type': self.type,
            'name': self.name,
            'model': self.inner_model,
            'E_CPU': float(E_CPU),
            'E_MEM': float(E_MEM),
            'E_GPU': float(E_GPU),
            'E': float(E),
            'I': float(I),
            'M': float(M),
            'SCI': float(SCI)
        }
        aggregated_metadata = {'aggregated': "True"}
        aggregated_observations = {}
        aggregated_components = node_metrics

        print(aggregated_metrics)
        toto = {}
        toto[self.name] = SCIImpactMetricsInterface(
            metrics=aggregated_metrics,
            metadata=aggregated_metadata,
            observations=aggregated_observations,
            components_list=aggregated_components
        )
        return toto