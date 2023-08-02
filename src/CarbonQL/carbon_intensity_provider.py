class CarbonIntensityProvider:
    def __init__(self, source):
        self.source = source

    def get_carbon_intensity(self):
        # Implementation of get_carbon_intensity method
        print("returning carbon intensity default value : 100")
        return 100
        pass


##############################

import os
import yaml
from datetime import datetime, timedelta

class EnvVarCarbonIntensity:
    def __init__(self, env_var_name):
        self.env_var_name = env_var_name

    def get_carbon_intensity(self):
        # Get the carbon intensity data from the environment variable
        data = os.environ.get(self.env_var_name)

        # Parse the YAML data
        carbon_data = yaml.safe_load(data)

        # Check if the data is fresh
        last_heartbeat_time = datetime.fromisoformat(carbon_data['lastHeartbeatTime'])
        if datetime.now() - last_heartbeat_time > timedelta(hours=24):
            # Log a warning if the data is stale
            print('WARNING: Carbon intensity data is stale')

            # Calculate the average carbon intensity value
            emissions_data = carbon_data['binarydata']['data']
            total_intensity = sum([d['intensity']['actual'] for d in emissions_data])
            average_intensity = total_intensity / len(emissions_data)

            return average_intensity
        else:
            # Get the current time
            now = datetime.now()

            # Find the closest time in the emissions data
            emissions_data = carbon_data['binarydata']['data']
            closest_time = None
            closest_diff = None
            for d in emissions_data:
                forecast_time = datetime.fromisoformat(d['from'])
                diff = abs(now - forecast_time)
                if closest_time is None or diff < closest_diff:
                    closest_time = forecast_time
                    closest_diff = diff

            # Return the carbon intensity for the closest time
            for d in emissions_data:
                forecast_time = datetime.fromisoformat(d['from'])
                if forecast_time == closest_time:
                    return d['intensity']['actual']



    



#############################
from kubernetes import client, config

class K8sCarbonIntensityConfigMap(CarbonIntensityProvider):
    def __init__(self, config_map_name, config_map_key):
        self.config_map_name = config_map_name
        self.config_map_key = config_map_key

        # Load the Kubernetes configuration
        config.load_incluster_config()

        # Create a Kubernetes API client
        self.api_client = client.CoreV1Api()

    def get_carbon_intensity(self):
        # Get the ConfigMap data
        config_map = self.api_client.read_namespaced_config_map(self.config_map_name, 'default')
        data = config_map.data[self.config_map_key]

        # Parse the data and return the carbon intensity value
        carbon_intensity = float(data)
        return carbon_intensity