from lib.ief.core import ImpactNodeInterface, ImpactModelPluginInterface, CarbonIntensityPluginInterface
from azure.identity import DefaultAzureCredential
from abc import abstractmethod

class AzureImpactNode(ImpactNodeInterface):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata)
        self.credential = DefaultAzureCredential()

    def authenticate(self, auth_params):
        pass

    @abstractmethod
    def list_supported_skus(self):
        pass