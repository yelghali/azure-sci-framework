curl -X POST \
  http://localhost:8000/metrics \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "e-shop",
    "components": [
        {
            "name": "webserver",
            "auth_params": {
                "your_auth_param_key": "your_auth_param_value"
            },
            "type": "AzureVM",
            "resource_selectors": {
                "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
                "resource_group": "webapprename",
                "name": "tototatar"
            },
            "metadata": {
                "your_metadata_key": "your_metadata_value"
            }
        },
               

    ],
    "interval": "PT1M",
    "timespan": "PT1H"
}'


######"


curl -X POST \
  http://localhost:8000/metrics \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "e-shop",
    "components": [
                {
            "name": "batchprocessing",
            "auth_params": {
                "key": "value"
            },
            "type": "AKSPod",
            "resource_selectors": {
                "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
                "resource_group": "sus-aks-lab",
                "cluster_name": "sus-aks-lab",
                "namespace": "keda",
                "prometheus_endpoint": "https://defaultazuremonitorworkspace-neu-b44y.northeurope.prometheus.monitor.azure.com"
                },
            "metadata": {
                "your_metadata_key": "your_metadata_value"
            }
        }

    ],
    "interval": "PT1M",
    "timespan": "PT1H"
}'