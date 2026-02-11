import os
from urllib.parse import urljoin

def before_all(context):
    generic = os.getenv("SUT_URL")

    # Service-specific 
    prometheus = os.getenv("PROMETHEUS_SUT_URL")
    alertmanager = os.getenv("ALERTMANAGER_SUT_URL")
    influx = os.getenv("INFLUXDB_SUT_URL")

    # Pick whatever is set 
    context.base_url = prometheus or alertmanager or influx or generic
    if not context.base_url:
        raise RuntimeError("No SUT URL set. Provide PROMETHEUS_SUT_URL / ALERTMANAGER_SUT_URL / INFLUXDB_SUT_URL or SUT_URL")

    context.timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    context.verify_tls = os.getenv("HTTP_VERIFY_TLS", "true").lower() == "true"
    context.default_headers = {}

def before_scenario(context, scenario):
    # Reset per scenario
    context.latencies_ms = []
    context.successful_requests = 0
    context.total_requests = 0
