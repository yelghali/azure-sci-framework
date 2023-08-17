# Use cases
* AS a developer, I want to estimate the carbon impact of my application (which uses several infrastructure components)
* As a developer / admin, I want to be able to see the carbon impact of my application over time (in dashboards)

# This project is a POC of the ief framework in pyhton (wip to converge wuth the final ief spec)

This project is an implementation of the Impact engine Framework, that provides : 
* An API : to calculate carbon metrics of an application (ad-hoc)
* A metrics exporter : which allows to build impact dashboards to help reduce carbon impact
* A python implementation of the framework 
* An SCI model for compute server, based on the SCI study case : https://github.com/Green-Software-Foundation/sci-guide/blob/dev/use-case-submissions/dow-msft-Graph-DB.md


## How it works

### built-in objects : ImpactModels, ImpactNodes, ImpactMetrics
![image](https://github.com/yelghali/imapct-engine-framework/assets/966110/0466f19c-6e9b-4c93-8596-1874e4223280)


The impactModel is the low level object that defines the impact calculation (here SCI), and the impact metrics that are used in the equation (CPU, RAM, GPU for SCI)

The impactNode is the object that represents the infrastructure component (VM, pod, etc..) ; it is associated to an impactModel. It fetches the metrics from the infrastructure component, and calculates the model.calculate to return an imapctMetric.

### the user experience

![image](https://github.com/yelghali/imapct-engine-framework/assets/966110/3156c2f9-49ad-4cf0-989c-d74d843bf093)

the user creates an impactRequest (Yaml, json) that describes the application, and the resources it uses (VMs, pods, etc..) ; and the timespan over which he wants to get the carbon impact of the application (R in the SCI equation)

the user sends the impactRequest to the Impact Engine API or CLI, which returns the carbon impact of the application (SCI) ; and the carbon impact of each resource used by the application (E, I, M)


### the current implementation

* Model : SCI based on the [DOW study case](https://github.com/Green-Software-Foundation/sci-guide/blob/dev/use-case-submissions/dow-msft-Graph-DB.md) (can be used for any compute server)

* Components (or impactNodes) : AzureVM, AKSNode, AKSPod, AzureFunction -> all use the same model


## example of an API call to get emissions of a VM based App

In this example, our app e-shop, has a **dedicated** VM, and we want to get the carbon impact of the application over the last 24 hour (timespan).

so SCI of e-shop App = SCI of VM (because the VM is not shared with other apps)

### query
```bash

curl -X POST \
  http://localhost:8000/metrics \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "e-shop",
    "components": [
        {
            "name": "webserver",
            "auth_params": {
            },
            "type": "AzureVM",
            "resource_selectors": {
                "subscription_id": "<SUbID>",
                "resource_group": "<RGName>",
                "name": "tototatar"
            },
            "metadata": {
                "your_metadata_key": "your_metadata_value"
            }
        }        

    ],
    "interval": "PT1M", # to normlize or homogenize the metrics collected from different sources ; this is a technical parameter ; TODO : remove from query
    "timespan": "PT24H"  # the R of SCI equation (time span)
}'
```

### response
```json
{
	"e-shop": {
		"name": "e-shop",
		"unit": "severalUnits",
		"type": "aggregatedimpactnode",
		"model": "sumofcomponents",
		"description": "Description of SCI Impact Metrics",
		"timespan": "PT24H",
		"interval": "PT1M",
		"E_CPU": 1.152,
		"E_MEM": 0.6218425726807492,
		"E_GPU": 0.0,
		"E": 1.7738425726807492,
		"I": 100.0,
		"M": 4.280821917808219e-05,
		"SCI": 177.3843000762941,
		"metadata": {
			"aggregated": "True"
		},
		"observations": {},
		"components": [{
			"tototatar": {
				"name": "tototatar",
				"unit": "severalUnits",
				"type": "azurevm",
				"model": "computeserver_static_imp",
				"description": "Description of SCI Impact Metrics",
				"timespan": "PT24H",
				"interval": "PT1M",
				"E_CPU": 1.152,
				"E_MEM": 0.6218425726807492,
				"E_GPU": 0.0,
				"E": 1.7738425726807492,
				"I": 100.0,
				"M": 4.280821917808219e-05,
				"SCI": 177.3843000762941,
				"metadata": {
					"resource_name": "tototatar"
				},
				"observations": {
					"average_cpu_percentage": 2.4472038327526153,
					"average_memory_gb": 1.6364278228440767,
					"average_gpu_percentage": 0
				},
				"components": [],
				"host_node": {}
			}
		}],
		"host_node": {}
	}
}
```


## example of code to get emissions of a "shared VM" based App


In this example, our app e-shop, has a **shared** VM, and we want to get the carbon impact of the application over the last 24 hour (timespan).

### query
```python

auth_params = {
}

resource_selectors = {
    "subscription_id": "<SUB>",
    "resource_group": "<RG>",
    "name": "<VMName>",
}

metadata = {
    "region": "westeurope"
}

timespan = "PT24H"
interval = "PT5M"

vm = AzureVM(name = "mywebserver", model = ComputeServer_STATIC_IMP(),  
             carbon_intensity_provider=None, 
             auth_object=auth_params, 
             resource_selectors=resource_selectors, 
             metadata=metadata,
             timespan=timespan,
             interval=interval)

#print(vm.fetch_resources())
#print(vm.fetch_observations())
print(vm.calculate())

manual_observations = {
     "node_host_cpu_util_percent" : 50,
     "node_host_memory_util_percent" : 50,
     "node_host_gpu_util_percent" : 50
 }

workload = AttributedImpactNodeInterface(name = "myworkload", 
                                          host_node=vm, 
                                          carbon_intensity_provider=None, 
                                          metadata=metadata, 
                                          observations=manual_observations,
                                          timespan=timespan,
                                          interval=interval)
print(workload.calculate())
```


### response (Json of objects)
```python
{
	'myworkload': SCIImpactMetricsInterface(name = 'myworkload', unit = 'severalUnits', type = 'attributedimpactnode', model = 'attributedimpactfromnode', description = 'Description of SCI Impact Metrics', timespan = 'PT24H', interval = 'PT5M', E_CPU = 0.576, E_MEM = 0.31337428009815704, E_GPU = 0.0, E = 0.889374280098157, I = 100.0, M = 4.280821917808219e-05, SCI = 88.93747081803488, metadata = {
		'attributed': 'True',
		'host_node_name': 'mywebserver'
	}, observations = {
		'node_host_cpu_util_percent': 50,
		'node_host_memory_util_percent': 50,
		'node_host_gpu_util_percent': 50
	}, components = [], host_node = {
		'mywebserver': SCIImpactMetricsInterface(name = 'tototatar', unit = 'severalUnits', type = 'azurevm', model = 'computeserver_static_imp', description = 'Description of SCI Impact Metrics', timespan = 'PT24H', interval = 'PT5M', E_CPU = 1.152, E_MEM = 0.6267485601963141, E_GPU = 0.0, E = 1.778748560196314, I = 100.0, M = 4.280821917808219e-05, SCI = 177.8748988278506, metadata = {
			'resource_name': 'tototatar'
		}, observations = {
			'average_cpu_percentage': 2.9743745726495727,
			'average_memory_gb': 1.6493383163060897,
			'average_gpu_percentage': 0
		}, components = [], host_node = {})
	})
}
```



## example of an API call to get emissions of a Kubernetes based App

In this example, our App is deployed on an AKS cluster, and we want to get the carbon impact of the application over the last 24 hour (timespan).

we define resource selectors to select the resources we want to get the carbon impact of. In this case, we want to get the carbon impact of the keda namespace, which contains the keda operator and the keda metrics server.

we also define the prometheus endpoint, which is the endpoint of the prometheus server that is used by the keda metrics server to get metrics from the cluster.

Our App is composed in this case of 2 pods, each pod running on a node (could be same node, or different one) 

The Imapct of a pod, is deducated from the impact of the node it is running on. (attribution pattern) ; and we use % pod utl of node resouces ( average % CPU, % of memory and % of GPU) -> during the timespan defined by the query

so :
* SCI of e-shop App = sum of SCI of pods ; 
* and SCI of pod = SCI of node * % of node resources used by the pod

### query

```bash


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
                "subscription_id": "<SUB>",
                "resource_group": "<RG>",
                "cluster_name": "<cluster>",
                "namespace": "keda", 
                "prometheus_endpoint": "<Prom endpoint>"
                },
            "metadata": {
                "your_metadata_key": "your_metadata_value"
            }
        }

    ],
    "interval": "PT5M", # to normlize or homogenize the metrics collected from different sources ; this is a technical parameter ; 
    "timespan": "PT24H" # the R of SCI equation (time span)
}'
```	

### response
```json

{
	"e-shop": {
		"name": "e-shop",
		"unit": "severalUnits",
		"type": "aggregatedimpactnode",
		"model": "sumofcomponents",
		"description": "Description of SCI Impact Metrics",
		"timespan": "PT24H",
		"interval": "PT5M",
		"E_CPU": 1.0295646315789783e-05,
		"E_MEM": 0.0,
		"E_GPU": 0.0,
		"E": 1.0295646315789783e-05,
		"I": 100.0,
		"M": 3.567351598173516e-06,
		"SCI": 0.0010331319831771517,
		"metadata": {
			"aggregated": "True"
		},
		"observations": {},
		"components": [{
			"keda-metrics-apiserver-5bcc58d658-mxqh7": {
				"name": "keda-metrics-apiserver-5bcc58d658-mxqh7",
				"unit": "severalUnits",
				"type": "attributedimpactnode",
				"model": "attributedimpactfromnode",
				"description": "Description of SCI Impact Metrics",
				"timespan": "PT1H",
				"interval": "PT5M",
				"E_CPU": 7.680000000002207e-06,
				"E_MEM": 0.0,
				"E_GPU": 0.0,
				"E": 7.680000000002207e-06,
				"I": 100.0,
				"M": 1.783675799086758e-06,
				"SCI": 0.0007697836757993074,
				"metadata": {
					"attributed": "True",
					"host_node_name": "aks-agentpool-23035252-vmss000005"
				},
				"observations": {
					"node_host_cpu_util_percent": 0.006000000000001724,
					"node_host_memory_util_percent": 0.046112060546875,
					"node_host_gpu_util_percent": 0
				},
				"components": [],
				"host_node": {
					"aks-agentpool-23035252-vmss000005": {
						"name": "aks-agentpool-23035252-vmss000005",
						"unit": "severalUnits",
						"type": "azurevm",
						"model": "computeserver_static_imp",
						"description": "Description of SCI Impact Metrics",
						"timespan": "PT1H",
						"interval": "PT5M",
						"E_CPU": 0.128,
						"E_MEM": 0.0,
						"E_GPU": 0.0,
						"E": 0.128,
						"I": 100.0,
						"M": 1.783675799086758e-06,
						"SCI": 12.8000017836758,
						"metadata": {
							"resource_name": "aks-agentpool-23035252-vmss000005"
						},
						"observations": {
							"average_cpu_percentage": 12.436124999999999,
							"average_memory_gb": 0,
							"average_gpu_percentage": 0
						},
						"components": [],
						"host_node": {}
					}
				}
			},
			"keda-operator-778fb74497-m55gs": {
				"name": "keda-operator-778fb74497-m55gs",
				"unit": "severalUnits",
				"type": "attributedimpactnode",
				"model": "attributedimpactfromnode",
				"description": "Description of SCI Impact Metrics",
				"timespan": "PT1H",
				"interval": "PT5M",
				"E_CPU": 2.615646315787576e-06,
				"E_MEM": 0.0,
				"E_GPU": 0.0,
				"E": 2.615646315787576e-06,
				"I": 100.0,
				"M": 1.783675799086758e-06,
				"SCI": 0.00026334830737784437,
				"metadata": {
					"attributed": "True",
					"host_node_name": "aks-agentpool-23035252-vmss000005"
				},
				"observations": {
					"node_host_cpu_util_percent": 0.0020434736842090437,
					"node_host_memory_util_percent": 0.038562774658203125,
					"node_host_gpu_util_percent": 0
				},
				"components": [],
				"host_node": {
					"aks-agentpool-23035252-vmss000005": {
						"name": "aks-agentpool-23035252-vmss000005",
						"unit": "severalUnits",
						"type": "azurevm",
						"model": "computeserver_static_imp",
						"description": "Description of SCI Impact Metrics",
						"timespan": "PT1H",
						"interval": "PT5M",
						"E_CPU": 0.128,
						"E_MEM": 0.0,
						"E_GPU": 0.0,
						"E": 0.128,
						"I": 100.0,
						"M": 1.783675799086758e-06,
						"SCI": 12.8000017836758,
						"metadata": {
							"resource_name": "aks-agentpool-23035252-vmss000005"
						},
						"observations": {
							"average_cpu_percentage": 12.436124999999999,
							"average_memory_gb": 0,
							"average_gpu_percentage": 0
						},
						"components": [],
						"host_node": {}
					}
				}
			}
		}],
		"host_node": {}
	}
}

```
