import logfire

metrics_tasks_total = logfire.metric_gauge(
    "tasks.total", description="Total number of tasks by type"
)
metrics_tasks_duration = logfire.metric_histogram(
    "tasks.duration_seconds", description="Task execution time in seconds"
)
metrics_ws_active = logfire.metric_gauge(
    "ws.active", description="Active WS connections"
)
