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
    timespan: str 
    interval: str
    E_CPU: float
    E_MEM: float
    E_GPU: float
    E: float
    I: float
    M: float
    SCI: float

    metadata: Dict[str, str] = {}
    observations: Dict[str, object] = {}
    static_params: Dict[str, object] = {}
    components: List[Dict[str,'SCIImpactMetricsInterface']] = []
    host_node : Dict[str, 'SCIImpactMetricsInterface'] = {}

    def __init__(self, metrics: Dict[str, float], metadata: Dict[str, str] = None, static_params : Dict[str, object] = None ,observations: Dict[str, object] = None, components_list: List['SCIImpactMetricsInterface'] = [], host_node : dict[str, 'SCIImpactMetricsInterface'] = {}):
        

        
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
            static_params=static_params,
            components=components_list,
            host_node = host_node,
            timespan = metrics.get('timespan', "PT1H"),
            interval = metrics.get('interval', "PT5M")
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
    def calculate(self, observations: Dict[str, object] = None, carbon_intensity : float = 100, interval : str = "PT5M", timespan : str = "PT1H", metadata : dict [str, str] = {}, static_params : dict[str,str] = None  ) -> Dict[str, SCIImpactMetricsInterface]:
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




aggregation = MetricAggregationType.AVERAGE

class ImpactNodeInterface(ABC):
    def __init__(self, name, model: ImpactModelPluginInterface = None, carbon_intensity_provider: CarbonIntensityPluginInterface = None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {}, interval : str = "PT5M", timespan : str = "PT1H"):
        self.type = "impactnode"
        self.name = name if name is not None else "impactnode"
        self.inner_model = model
        self.carbon_intensity_provider = carbon_intensity_provider
        self.auth_object = auth_object
        self.resource_selectors = resource_selectors
        self.metadata = metadata
        self.resources = None
        self.observations = None
        self.interval = interval
        self.timespan = timespan

    # def run(self) -> Dict[str, object]:
    #     self.authenticate(self.auth_object.get_auth_params())
    #     self.resources = self.fetch_resources()
    #     self.static_params = self.lookup_static_params()
    #     self.configure(self.name, self.static_params)
    #     self.observations = self.fetch_observation()
    #     return self.calculate(self.observations)

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

    def lookup_static_params(self) -> Dict[str, object]:
        #lookup the static params for the model, corresponding to the fetched resources
        pass

    def calculate(self, carbon_intensity : float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        self.fetch_resources()
        self.fetch_observations()
        return self.inner_model.calculate(observations=self.observations, carbon_intensity=carbon_intensity, timespan=self.timespan, interval= self.interval, metadata=self.metadata)

    def model_identifier(self) -> str:
        return self.inner_model.model_identifier()

    def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactNodeInterface':
        return self.inner_model.configure(name, static_params)



class AggregatedImpactNodesInterface(ABC):
    def __init__(self, name, components : List[ImpactNodeInterface], carbon_intensity_provider: CarbonIntensityPluginInterface = None, type=None, model=None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {}, interval : str = "PT5M", timespan : str = "PT1H" ):
        self.components = components  
        self.resource_selectors = resource_selectors
        self.metadata = metadata
        self.inner_model = "sumofcomponents"
        self.type = type if type is not None else "aggregatedimpactnode"
        self.name = name if name is not None else "aggregatedimpactnode"
        self.carbon_intensity_provider = carbon_intensity_provider
        self.auth_object = auth_object
        self.interval = interval
        self.timespan = timespan


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
            
            component.interval = self.interval
            component.timespan = self.timespan
            component.fetch_observations()

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
            'timespan' : self.timespan,
            'interval' : self.interval,
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
        static_params = {}
        aggregated_components = node_metrics

        print(aggregated_metrics)
        toto = {}
        toto[self.name] = SCIImpactMetricsInterface(
            metrics=aggregated_metrics,
            metadata=aggregated_metadata,
            observations=aggregated_observations,
            static_params=static_params,
            components_list=aggregated_components
        )
        return toto
    

class AttributedImpactNodeInterface(ABC):

    def __init__(self, name, host_node : ImpactNodeInterface = None, model: ImpactModelPluginInterface = None, carbon_intensity_provider: CarbonIntensityPluginInterface = None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {}, observations: Dict = None, interval : str = "PT5M", timespan : str = "PT1H"):
        self.type = "attributedimpactnode"
        self.inner_model = "attributedimpactfromnode" #not using a model for now, using attribute_impact_from_host_node func
        self.carbon_intensity_provider = carbon_intensity_provider
        self.auth_object = auth_object
        self.resource_selectors = resource_selectors
        self.metadata = metadata
        self.resources = None
        self.observations = observations
        self.host_node = host_node
        self.name = name if name is not None else "attributedimpactnode"
        self.interval = interval
        self.timespan = timespan


    def attribute_impact_from_host_node(self, host_impact = SCIImpactMetricsInterface, observations = Dict[str, object], carbon_intensity = 100) -> Dict[str, SCIImpactMetricsInterface]:
        #return a SCIImpactMetricsInterface object
        
        E_CPU = host_impact.E_CPU * observations.get("node_host_cpu_util_percent", 0) / 100
        E_MEM = host_impact.E_MEM * observations.get("node_host_memory_util_percent", 0) / 100
        E_GPU = host_impact.E_GPU * observations.get("node_host_gpu_util_percent", 0) / 100
        E = E_CPU + E_MEM + E_GPU
        I = carbon_intensity
        M = host_impact.M #TODO : change this to be calculated from the host node
        SCI = (E * I) + M

        # Create a new SCIImpactMetricsInterface instance with the calculated metrics
        attributed_metrics = {
            'name' : self.name,
            'type': self.type,
            'model': self.inner_model,
            'timespan' : self.timespan,
            'interval' : self.interval,
            'E_CPU': float(E_CPU),
            'E_MEM': float(E_MEM),
            'E_GPU': float(E_GPU),
            'E': float(E),
            'I': float(I),
            'M': float(M),
            'SCI': float(SCI)
        }
        metadata = {'attributed': "True", "host_node_name": self.host_node.name}
        components = []

        toto = {}
        toto[self.name] = SCIImpactMetricsInterface(
            metrics=attributed_metrics,
            metadata=metadata,
            observations=observations,
            components_list=components,
            host_node={self.host_node.name : host_impact}
        )
        return toto

    def calculate(self, carbon_intensity: float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        if self.host_node is None:
            raise ValueError('Host node is not set')
        
        if self.observations is None:
            raise ValueError('Observations are not set')
        
        self.host_node.fetch_resources()

        self.host_node.interval = self.interval
        self.host_node.timespan = self.timespan
        self.host_node.fetch_observations()

        host_impact_dict = self.host_node.calculate(carbon_intensity=carbon_intensity)

        host_impact = list(host_impact_dict.values())[0]

        node_metric = self.attribute_impact_from_host_node(host_impact, self.observations, carbon_intensity=carbon_intensity)
        return node_metric