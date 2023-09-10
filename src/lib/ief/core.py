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
    def calculate(self, observations: Dict[str, object] = None, carbon_intensity : CarbonIntensityPluginInterface  = None, interval : str = "PT5M", timespan : str = "PT1H", metadata : dict [str, str] = {}, static_params : dict[str,str] = None  ) -> Dict[str, SCIImpactMetricsInterface]:
        pass





aggregation = MetricAggregationType.AVERAGE

class ImpactNodeInterface(ABC):
    def __init__(self, name, model: ImpactModelPluginInterface = None, carbon_intensity_provider: CarbonIntensityPluginInterface = None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {}, interval : str = "PT5M", timespan : str = "PT1H", params : Dict[str, object] = {}):
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
        self.params = params

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
    async def fetch_resources(self) -> Dict[str, object]:
        #using label selectors, fetch resources from cloud provider
        pass

    @abstractmethod
    async def fetch_observations(self) -> Dict[str, object]:
        #using label selectors, fetch observation from cloud provider
        pass

    async def lookup_static_params(self) -> Dict[str, object]:
        #lookup the static params for the model, corresponding to the fetched resources
        pass

    async def calculate(self, carbon_intensity : CarbonIntensityPluginInterface  = None) -> Dict[str, SCIImpactMetricsInterface]:
        await self.fetch_resources()
        await self.lookup_static_params()
        await self.fetch_observations()
        return await self.inner_model.calculate(observations=self.observations, carbon_intensity=carbon_intensity, timespan=self.timespan, interval= self.interval, metadata=self.metadata)

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

    def calculate(self, carbon_intensity: CarbonIntensityPluginInterface  = None) -> Dict[str, SCIImpactMetricsInterface]:
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

            carbon_intensity_provider = self.carbon_intensity_provider
            impact_metrics = component.calculate(carbon_intensity=carbon_intensity_provider)

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

    def __init__(self, name, host_node_impact_dict : dict = {}, host_node_static_params : dict = {},host_node_model: ImpactModelPluginInterface = None, carbon_intensity_provider: CarbonIntensityPluginInterface = None, auth_object: AuthParams = {}, resource_selectors: Dict[str, List[str]] = {}, metadata: Dict[str, object] = {}, observations: Dict = None, interval : str = "PT5M", timespan : str = "PT1H", static_params : dict = {}):
        self.type = "attributedimpactnode"
        self.inner_model = "attributedimpactfromnode" #not using a model for now, using attribute_impact_from_host_node func
        self.carbon_intensity_provider = carbon_intensity_provider
        self.auth_object = auth_object
        self.resource_selectors = resource_selectors
        self.metadata = metadata
        self.resources = None
        self.observations = observations
        self.static_params = static_params
        self.host_node_impact_dict = host_node_impact_dict
        self.host_node_static_params = host_node_static_params
        self.name = name if name is not None else "attributedimpactnode"
        self.interval = interval
        self.timespan = timespan
        self.host_node_model = host_node_model


    def attribute_impact_from_host_node(self, host_impact = SCIImpactMetricsInterface, observations = Dict[str, object], carbon_intensity : float = 100, host_static_params : dict = {}, self_static_parms : dict = {}, host_node_model : ImpactNodeInterface = None) -> Dict[str, SCIImpactMetricsInterface]:
        #return a SCIImpactMetricsInterface object, 
        

        print("host_impact observations : %s" % host_impact.observations)
        print("self observations %s" % observations)

        node_host_cpu_util_ratio = observations.get("average_cpu_percentage", 0) / host_impact.observations.get("average_cpu_percentage", 1) if host_impact.observations.get("average_cpu_percentage", 1) != 0 else 0
        node_host_memory_util_ratio = observations.get("average_memory_gb", 0) / host_impact.observations.get("average_memory_gb", 1) if host_impact.observations.get("average_memory_gb", 1) != 0 else 0
        node_host_gpu_util_ratio = 0 #TODO : add gpu util ratio

        #add to self observations dict
        observations["node_host_cpu_util_ratio"] = node_host_cpu_util_ratio
        observations["node_host_memory_util_ratio"] = node_host_memory_util_ratio
        observations["node_host_gpu_util_ratio"] = node_host_gpu_util_ratio

        # Energy
        E_CPU = host_impact.E_CPU * node_host_cpu_util_ratio
        E_MEM = host_impact.E_MEM * node_host_memory_util_ratio
        E_GPU = host_impact.E_GPU * node_host_gpu_util_ratio
        E = E_CPU + E_MEM + E_GPU

        # Carbon Intensity
        I = carbon_intensity
        
        
        # Embodied Emisions (M)
        #prep pod_node_static_params, to call host_node_model.calculate_m
        pod_node_static_params = {}
        # te is node te
        # rr / instance cpu is pod cpu limit (gb)
        # total_vc is node instance cpu (rr of node)
        te = host_static_params.get("te", 0)
        print("te : %s" % te)
        #rr = self_static_parms.get("cpu_limit", 1)
        rr = observations.get("rr", 1)
        tr = observations.get("tr", 1)
        print("rr : %s" % rr)
        
        total_vc = host_static_params.get("total_vcpus", 4)
        print("total_vc : %s" % total_vc)
        M = host_node_model.calculate_m(te=te, rr=rr, total_vcpus=total_vc, timespan=self.timespan, tr = tr)
        print("pod M : %s" % M)
        MHost = host_impact.M #TODO : change this to be calculated from the host node
        print("host M : %s" % MHost)
        
        # SCI
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

        host_node_name = list(self.host_node_impact_dict.keys())[0]


        metadata = {'attributed': "True", "host_node_name": host_node_name}
        components = []
        static_params = self_static_parms


        toto = {}
        toto[self.name] = SCIImpactMetricsInterface(
            metrics=attributed_metrics,
            metadata=metadata,
            observations=observations,
            components_list=components,
            static_params=static_params,
            host_node={host_node_name: host_impact}
        )
        return toto

    async def calculate(self, carbon_intensity: CarbonIntensityPluginInterface  = None) -> Dict[str, SCIImpactMetricsInterface]:
        if self.host_node_impact_dict is None:
            raise ValueError('Host node impact value is not set')
        
        if self.observations is None:
            raise ValueError('self Observations are not set')
        
        #await self.host_node.fetch_resources()

        #self.host_node.interval = self.interval
        #self.host_node.timespan = self.timespan
        #await self.host_node.fetch_observations()

        #host_impact_dict = await self.host_node.calculate(carbon_intensity=carbon_intensity)

        host_impact = list(self.host_node_impact_dict.values())[0]
        host_static_params = list(self.host_node_static_params.values())[0]
        self_static_parms = self.static_params
        host_node_model = self.host_node_model

        if self.carbon_intensity_provider is None:
            Warning('Carbon Intensity Provider is not set, using default value of 100')
            carbon_intensity = 100
        else:
            CI = await self.carbon_intensity_provider.get_current_carbon_intensity()
            carbon_intensity = CI["value"]

        node_metric = self.attribute_impact_from_host_node(host_impact, self.observations, carbon_intensity=carbon_intensity, host_static_params=host_static_params, self_static_parms=self_static_parms, host_node_model=host_node_model)
        return node_metric