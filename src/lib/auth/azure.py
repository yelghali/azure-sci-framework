from lib.ief.core import AuthParams
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AccessToken
from typing import Dict


class AzureManagedIdentityAuthParams(AuthParams):
    def __init__(self, resource: str):
        self.resource = resource

    def get_auth_params(self) -> Dict[str, str]:


        credential = DefaultAzureCredential()
        token = credential.get_token(self.resource)
        return {'Authorization': f'Bearer {token.token}'}