import requests
from typing import Dict, Any
from lib.components.azure_base import AzureImpactNode
from lib.ief.core import SCIImpactMetricsInterface
from lib.auth.azure import AzureManagedIdentityAuthParams

from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.identity import DefaultAzureCredential

class AzureFunction(AzureImpactNode):
    def __init__(self, name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval="PT5M", timespan="PT1H"):
        super().__init__(name, model, carbon_intensity_provider, auth_object, resource_selectors, metadata, interval, timespan)
        self.type = "azurefunction"
        self.resources = {}
        self.observations = {}
        self.credential = DefaultAzureCredential()

    def get_auth_token(self):
        scope = "https://prometheus.monitor.azure.com/.default"
        token = self.credential.get_token(scope)
        return token.token

    def fetch_resources(self) -> Dict[str, Any]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        resource_group_name = self.resource_selectors.get("resource_group", None)
        function_app_name = self.resource_selectors.get("function_app_name", None)

        resource_client = ResourceManagementClient(self.credential, subscription_id)
        function_app = resource_client.resources.get_by_id(
            resource_id=f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{function_app_name}",
            api_version="2019-08-01"
        )

        self.resources = function_app
        return function_app

    def fetch_observations(self) -> Dict[str, Any]:
        subscription_id = self.resource_selectors.get("subscription_id", None)
        function_app_name = self.resource_selectors.get("function_app_name", None)

        monitor_client = MonitorManagementClient(self.credential, subscription_id)

        # Fetch function app telemetry
        telemetry_data = monitor_client.metrics.list(
            resource_uri=f"/subscriptions/{subscription_id}/resourceGroups/{self.resources.resource_group}/providers/Microsoft.Web/sites/{function_app_name}",
            metricnames='Percentage CPU, Available Memory Bytes',
            aggregation='Average',
            interval=self.interval,
            timespan=self.timespan
        )

        # Calculate the average percentage CPU and available memory bytes
        cpu_percentage = 0
        available_memory_bytes = 0
        for metric in telemetry_data.value:
            for time_series in metric.timeseries:
                for data in time_series.data:
                    if data.average is not None:
                        if metric.name.localized_value == 'Percentage CPU':
                            cpu_percentage = data.average
                        elif metric.name.localized_value == 'Available Memory Bytes':
                            available_memory_bytes = data.average

        # Fetch function app duration
        duration_data = monitor_client.metrics.list(
            resource_uri=f"/subscriptions/{subscription_id}/resourceGroups/{self.resources.resource_group}/providers/Microsoft.Web/sites/{function_app_name}",
            metricnames='Function Execution Units',
            aggregation='Total',
            interval=self.interval,
            timespan=self.timespan
        )

        # Calculate the total duration of function running
        total_duration = 0
        for metric in duration_data.value:
            for time_series in metric.timeseries:
                for data in time_series.data:
                    if data.total is not None:
                        total_duration += data.total

        self.observations = {
            'cpu_percentage': cpu_percentage,
            'available_memory_bytes': available_memory_bytes,
            'total_duration': total_duration
        }

        return self.observations

    def calculate(self, carbon_intensity: float = 100) -> Dict[str, SCIImpactMetricsInterface]:
        self.fetch_resources()
        self.fetch_observations()
        return self.inner_model.calculate(self.observations, carbon_intensity=carbon_intensity, interval=self.interval, timespan=self.timespan, metadata=self.metadata)

    def lookup_static_params(self) -> Dict[str, Any]:
        return {}

    def query_prometheus(self, prometheus_endpoint: str, query: str, timespan: str, interval: str) -> Dict[str, Any]:
        url = f"{prometheus_endpoint}/api/v1/query"
        params = {
            "query": query,
            "start": f"now()-{timespan}",
            "end": "now()",
            "step": interval
        }

        params = {"query" : query}
        auth_token = self.get_auth_token()
        headers = {
            "Accept": "application/json",
            'Authorization': f'Bearer %s' % auth_token,
            'Content-Type' : 'application/x-www-form-urlencoded'
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Failed to query Prometheus: {response.text}")

        return response.json()