from prometheus_client import Counter


class Logger:
    def __init__(self):
        # Total request counter
        self.total_requests = Counter("total_requests", "Total number of API requests")

        # Failed request counter
        self.failed_requests = Counter(
            "failed_requests", "Total number of failed API requests"
        )

        # Per-route request counter
        self.route_requests = Counter(
            "route_requests", "Number of requests per route", ["method", "route"]
        )

        # Per-route failed request counter
        self.route_failures = Counter(
            "route_failures", "Number of failed requests per route", ["method", "route"]
        )

        # Distinct users gauge
        self.distinct_users = Counter(
            "distinct_users", "Number of distinct users making requests"
        )

        # Distinct apps gauge
        self.distinct_apps = Counter(
            "distinct_apps", "Number of distinct apps making requests"
        )

        self.cron = Counter("cron_task", "Number of cron tasks ran")

    def increment_total(self):
        """Increment total request counter"""
        self.total_requests.inc()

    def increment_failed(self):
        """Increment failed request counter"""
        self.failed_requests.inc()

    def increment_route(self, method: str, route: str):
        """Increment counter for specific route"""
        self.route_requests.labels(method=method, route=route).inc()

    def increment_route_failure(self, method: str, route: str):
        """Increment failure counter for specific route"""
        self.route_failures.labels(method=method, route=route).inc()

    def set_distinct_users(self, count: int):
        """Set gauge for number of distinct users"""
        self.distinct_users.set(count)

    def set_distinct_apps(self, count: int):
        """Set gauge for number of distinct apps"""
        self.distinct_apps.set(count)

    def increment_cron(self):
        self.cron.inc()


logger = Logger()
