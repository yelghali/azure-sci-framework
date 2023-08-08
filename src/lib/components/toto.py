def fetch_observations(self, node_name, resource_group_name, timespan, interval):
    monitor_client = self._get_monitor_client()
    node_id = self._get_node_id(node_name, resource_group_name)
    cpu_utilization = []
    ram_consumed = []
    gpu_utilization = []
    for metric_name in ['Percentage CPU', 'Memory Usage', 'GPU Utilization']:
        metrics_data = monitor_client.metrics.list(
            resource_uri=node_id,
            metricnames=metric_name,
            interval=interval,
            timespan=timespan
        )
        for metric in metrics_data.value:
            if metric.name.value == metric_name:
                if metric_name == 'Percentage CPU':
                    cpu_utilization.extend([datapoint.average for timeserie in metric.timeseries for datapoint in timeserie.data])
                elif metric_name == 'Memory Usage':
                    ram_consumed.extend([datapoint.average / 1024 ** 3 for timeserie in metric.timeseries for datapoint in timeserie.data])
                elif metric_name == 'GPU Utilization':
                    gpu_utilization.extend([datapoint.average for timeserie in metric.timeseries for datapoint in timeserie.data])
    return cpu_utilization, ram_consumed, gpu_utilization