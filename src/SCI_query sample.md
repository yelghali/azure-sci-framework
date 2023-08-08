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
        {
            "name": "sqlserver",
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
            
        {
            "name": "batchprocessing",
            "auth_params": {
                "your_auth_param_key": "your_auth_param_value"
            },
            "type": "AKSNode",
            "resource_selectors": {
                "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
                "resource_group": "sus-aks-lab",
                "cluster_name": "sus-aks-lab",
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







100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle",instance=~"aks-agentpool-23035252-vmss000005|aks-np2-39168539-vmss000000"}[5m])) * 100)