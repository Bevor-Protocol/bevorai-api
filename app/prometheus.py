from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.utils import INF


class PromLogger:
    def __init__(self):
        # Queue metrics
        # Intuitively a lot of these can be Counters, but I'm a bit limited
        # in terms of what Arq reports to me via its healthcheck
        self.tasks_info = Gauge(
            "tasks_total", "Total number of tasks by type", ["type"]
        )

        self.tasks_enqueue_duration = Histogram(
            "tasks_enqueue_duration_seconds",
            "Task enqueueing time until job start in seconds",
        )

        # I anticipate some long tasks here (hence why a queue is used). Don't use the default. # noqa
        self.tasks_duration = Histogram(
            "tasks_duration_seconds",
            "Task execution time in seconds",
            buckets=(
                0.01,
                0.025,
                0.05,
                0.1,
                0.5,
                1.0,
                5.0,
                10.0,
                20.0,
                30.0,
                45.0,
                60.0,
                INF,
            ),
        )

        # API metrics
        self.api_requests = Counter(
            "api_requests_total",
            "Total number of API requests",
            ["method", "endpoint", "status_code"],
        )

        # Default bucketing is fine here, it's generally catered towards api request times. # noqa
        self.api_duration = Histogram(
            "api_duration_seconds",
            "API request duration in seconds",
            ["method", "endpoint"],
        )

        self.api_active = Gauge(
            "api_active_requests_total",
            "Total active API requests",
        )

        self.websockets = Gauge("websockets_active_total", "Total active websockets")


prom_logger = PromLogger()
