from abc import ABC, abstractmethod
from typing import Dict, List
from pydantic import BaseModel


class AuthParams(ABC):
    @abstractmethod
    def get_auth_params(self) -> Dict[str, str]:
        pass


class SCIImpactMetricsInterface(BaseModel):
    name: str = "SCI Impact Metrics"
    unit: str = "severalUnits"
    model : str = "SCI Impact Model"
    description: str = "Description of SCI Impact Metrics"
    E_CPU: float
    E_MEM: float
    E_GPU: float
    E: float
    I: float
    M: float
    SCI: float
    metadata: Dict[str, str] = None
    observations: Dict[str, object] = None

    def __init__(self, metrics: Dict[str, float], metadata: Dict[str, str] = None, observations: Dict[str, object] = None):
        super().__init__(
        name = metrics.get('name'),
        model = metrics.get('model'),
        E_CPU = metrics.get('E_CPU'),
        E_MEM = metrics.get('E_MEM'),
        E_GPU = metrics.get('E_GPU'),
        E = metrics.get('E'),
        I = metrics.get('I'),
        M = metrics.get('M'),
        SCI = metrics.get('SCI'),
        metadata = metadata,
        observations = observations)



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



class ImpactNodeInterface(ABC):
    def __init__(self, model: ImpactModelPluginInterface, carbon_intensity_provider: CarbonIntensityPluginInterface, auth_object: AuthParams, resource_selectors: Dict[str, List[str]], metadata: Dict[str, object]):
        self.type = "ImpactNodeInterface"
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
        return self.inner_model.calculate(self.observations, carbon_intensity=carbon_intensity)

    def model_identifier(self) -> str:
        return self.inner_model.model_identifier()

    def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactNodeInterface':
        return self.inner_model.configure(name, static_params)



