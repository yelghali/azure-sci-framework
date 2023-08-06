from abc import ABC, abstractmethod
from typing import Dict, List


class AuthParams(ABC):
    @abstractmethod
    def get_auth_params(self) -> Dict[str, str]:
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
    def calculate(self, observations: Dict[str, object] = None, carbon_intensity : float = 100) -> Dict[str, object]:
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
        self.name = "ImpactNodeInterface"
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

    def calculate(self, carbon_intensity : float = 100) -> Dict[str, object]:
        return self.inner_model.calculate(self.observations, carbon_intensity=carbon_intensity)

    def model_identifier(self) -> str:
        return self.inner_model.model_identifier()

    def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactNodeInterface':
        return self.inner_model.configure(name, static_params)



