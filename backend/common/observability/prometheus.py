from prometheus_client import Counter, Gauge, Histogram

# Warning: this value is tightly coupled to the following locations; changes must be kept in sync, otherwise
# Grafana metric queries will fail:
# - deploy/backend/grafana/fba_datasource.yml
# - deploy/backend/grafana/dashboards/fba_server.json
PROMETHEUS_APP_NAME = 'fba_server'

PROMETHEUS_REQUEST_IN_PROGRESS_GAUGE = Gauge(
    name='fba_request_in_progress',
    documentation='Gauge of requests in progress by method and path',
    labelnames=['app_name', 'method', 'path'],
)

PROMETHEUS_REQUEST_COUNTER = Counter(
    name='fba_request_total',
    documentation='Total request count by method and path',
    labelnames=['app_name', 'method', 'path'],
)

PROMETHEUS_REQUEST_COST_TIME_HISTOGRAM = Histogram(
    name='fba_request_cost_time',
    documentation='Histogram of request duration by method and path (in ms)',
    labelnames=['app_name', 'method', 'path'],
)

PROMETHEUS_EXCEPTION_COUNTER = Counter(
    name='fba_exception_total',
    documentation='Total exception count by method, path and exception type',
    labelnames=['app_name', 'method', 'path', 'exception_type'],
)


PROMETHEUS_RESPONSE_COUNTER = Counter(
    name='fba_response_total',
    documentation='Total response count by method, path and status code',
    labelnames=['app_name', 'method', 'path', 'status_code'],
)
