curl -X POST \
  http://localhost:8000/metrics \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "your_app_name",
    "components": [
        {
            "name": "your_component_name",
            "auth_params": {
                "your_auth_param_key": "your_auth_param_value"
            },
            "type": "your_component_type",
            "resource_selectors": {
                "subscription_id": "0f4bda7e-1203-4f11-9a85-22653e9af4b4",
                "resource_group": "webapprename",
                "name": "tototatar"
            },
            "metadata": {
                "your_metadata_key": "your_metadata_value"
            }
        }
    ],
    "interval": "PT1M",
    "timespan": "PT1H"
}'