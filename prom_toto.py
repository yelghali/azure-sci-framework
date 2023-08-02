from prometheus_client import start_http_server, Counter, Summary
import random
import time

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds',
                       'Time spent processing request')


# Decorate function with metric.
@REQUEST_TIME.time()
def process_request(t):
    """A dummy function that takes some time."""
    time.sleep(t)


if __name__ == '__main__':
    my_counter1 = Counter('my_counter1', 'My counter')
    # Start up the server to expose the metrics.
    start_http_server(8000)
    # Generate some requests.
    while True:
        my_counter1.inc()
        process_request(random.random())