from lib.ief.core import ImpactModelPluginInterface
from typing import Dict, List


class ComputeServer_STATIC_IMP(ImpactModelPluginInterface):
    def __init__(self):
        super().__init__()
        self.name = "ComputeServer_STATIC_IMP"
        self.static_params = None

    def model_identifier(self) -> str:
        return self.name

    async def configure(self, name: str, static_params: Dict[str, object] = None) -> 'ImpactModelPluginInterface':
        self.name = name
        self.static_params = static_params
        return self

    def authenticate(self, auth_params: Dict[str, object]) -> None:
        pass

    async def calculate(self, observations: Dict[str, object] = None) -> Dict[str, object]:
        return 57