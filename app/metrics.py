import logfire

metrics_tasks_total = logfire.metric_gauge(
    "tasks.total", description="Total number of tasks by type", unit="#"
)
metrics_tasks_duration = logfire.metric_gauge(
    "tasks.duration", description="Task execution time in seconds", unit="s"
)
metrics_ws_active = logfire.metric_gauge(
    "ws.active", description="Active WS connections", unit="#"
)
