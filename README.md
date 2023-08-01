# kubernetes-sci-exporter
Kubernetes exporter for Software Carbon Intensity metrics  ; c.f SCI specification from the Green Software Foundation


This exporter is based on the [Prometheus Python client] and serves to export SCI metrics from a Kubernetes cluster. c.f https://github.com/Green-Software-Foundation/sci/blob/main/Software_Carbon_Intensity/Software_Carbon_Intensity_Specification.md

Each hour, it exports the following metrics:
* `sci_node` - the SCI of each node
    * metadata:
        * cluster_name: the name of the cluster (string)
        * region:  the region of the cluster (string)
        * zone: the zone of the node pool, that the node belongs to (string)
        * node_name: the name of the node (string)
        * node_labels: the labels of the node (dict)
        * node_annotations: the annotations of the node (dict)
    * observations: (from prometheus metrics)
        * server_utilization: the server utilization of the node (%) (float) # from metrics workspace (Prometheus compatible api)
        * server_tdp_coefficient: the server TDP coefficient of the node (float) # calculated based on server_utilization
    * Exported SCI metrics:
        * E: the energy consumption of the node (kWh) (float)
        * I: the carbon intensity of the region (gCO2e/kWh) (float)
        * M : embodied carbon of the node (gCO2e) (float)
        * SCI : the carbon emissions of the node (gCO2e) (float)

* `sci_pod` - the SCI of each pod
// the energy E & embodied emissions M, of a pod are calculated based on the E & M of the hosting node. A simple model could use pode %utilization of the node, to then estimate an allocated % SCI from the SCI of the node.
// to do : details


## How it works
each hour, we calculate the SCI of each node, and export it as a metric. The SCI of a node is calculated as follows (from the example below based on a web app, a node is a VM, so we use a similar formula as below)

App server for Web application
Energy (E)
The Quantification method used for calculating energy value is Calculate. We are measuring CPU utilization of the app servers and then using a model based on the Thermal Design Power (TDP) of the processors, number of cores etc to estimate the power consumption.

The equation used to model the energy consumption is:

P[kwH] = (Power consumed by CPU or Pc Number of cores + Power consumed by Memory or Pr + Power consumed by GPU or Pg Number of GPUs)/1000

CPU Utilization doesn’t scale linearly with power consumption, we will use the power curve as described in the SCI Data Project “[E] Energy Estimation from Utilization Model” model
TDP of server used in Azure App server Premium configuration (P2v2 ) -2nd Generation Intel® Xeon® Platinum 8272CL (Cascade Lake)= 205 W ( https://ark.intel.com/content/www/us/en/ark/products/192482/intel-xeon-platinum-8270-processor-35-75m-cache-2-70-ghz.html)
From specs, we found that Power consumed by 4GB memory is close to 1.45 W and that by 8 GB memory is approximately 2.45 W. Also from this article we can consider power consumed is approx 0.38 W/GB or close to 2.6 Watts.Since the energy values for memory are much lower than the calculated energy values for processors or CPUs, we consider these values negligible. Pr ~0
No GPU was used hence Pg ~0
Carbon Intensity (I)
We will use regional yearly averages.
The region the application was run in was India.
We will source the Carbon Intensity from the SCI Data project and the [I] Regional Yearly Marginal Carbon Intensity data set.
Embodied Carbon (M)
The equation to calculate M = TE * (TR/EL) * (RR/TR)

Where:

TE = Total Embodied Emissions, the sum of LCA emissions for all hardware components associated with the application server.
TR = Time Reserved, the length of time the hardware is reserved for use by the software.
EL = Expected Lifespan, the anticipated time that the equipment will be installed.
RR = Resources Reserved, the number of resources reserved for use by the software.
TR = Total Resources, the total number of resources available.
For this component:

TE: We will source the embodied carbon estimates for the servers from the Cloud Carbon Footprint Coefficient Data Set.
TR: 1 hr.
EL: We will assume a 4 year lifespan or 35,040 hrs.
RR: A virtual machine with 2 vCPUs was used, this data was sourced from Cloud Carbon Footprint Azure Instances Coefficients.
TR: The bare metal host is split up into 16 vCPUs in total. This data was sourced from the Cloud Carbon Footprint Azure Instances Coefficients.


-----

(Quantify) Example of SCI Value Calculation
*Show your work! For each of the components of your software system, show how you arrived at the SCI value. Guidance for this is available in the Methodology summary section. *

App server for Web application
Energy (E)
The workings of E, include raw numbers and calculations.

Server utilization = 18.3922%
Number of hours = 1
Number of cores = 2
TDP = 205W
TDP Coefficient = 0.32
E = Server utilization * Number of hours * Number of cores * TDP * TDP co-efficient
  = (0.18 * 1 hour * 2 cores * 205 TDP * 0.32 TDP co-efficient)/1000
  = 0.023
E = 0.023 KwH for a 1 hour period

Carbon Intensity (I)
I = 951 gCO2e/kWh

Embodied Carbon (M)
M = TE * (TR/EL) * (RR/TR)

TE = 1205.52 kgCo2e
TR = 1 hour
EL = 35040
RR = 2
TR = 16
M = 1205.52 * (1/35040) * (2/16) = 0.004305 KG =~ 4.305 gCO2e

SCI
The sum of the SCI calculation.

SCI = (E * I) + M = (0.02394 KwH * 951 gCO2e/kwH) + 4.305 gCO2e = 26.178 gCO2e


---

in our scenario, the SCI metrics exporter get data from differnt sources:
* carbon intensity forecast in a configmap
* node TDP & other static metrics to calculate E & M in a configmap
* node metrics from prometheus metrics workspace to calculate E & M