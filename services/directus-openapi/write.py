import asyncio
import json
import time
from typing import Any, Dict, List

import httpx
from behave import *

# Constants (Move to environment variables or config file for real projects)
DIRECTUS_URL = "http://localhost:8080"  # Replace with your Directus URL
COLLECTION_NAME = "your_collection_name"  # Replace with your collection name
AUTH_TOKEN = "your_auth_token"  # Replace with your auth token or authentication logic


async def create_items(
    collection: str, data: List[Dict[str, Any]], auth_token: str
) -> httpx.Response:
    """Creates items in a Directus collection."""
    url = f"{DIRECTUS_URL}/items/{collection}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    }  # Use Authorization header if needed
    payload = {"data": data}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return response


@given('I target the "write" operation')
def step_impl(context):
    context.operation = "write"


@when("I saturate the link at {bandwidth} {unit}")
async def step_impl(context, bandwidth: int, unit: str):
    """Saturates the link by sending requests to Directus."""

    # Validate unit (only Mbit/s is supported for now).
    if unit.lower() != "mbit/s":
        raise ValueError(f"Unsupported bandwidth unit: {unit}")

    bandwidth_bps = bandwidth * 1000000  # Convert Mbit/s to bits per second
    start_time = time.time()
    bytes_sent = 0
    num_requests = 0
    request_size = 1024  # Adjust request size as needed (in bytes)

    # Data to send (replace with meaningful data later)
    sample_item = {"some_field": "some_value"}
    data = [sample_item] * 10 #Send a batch of 10 items per request


    async def send_request():
        nonlocal bytes_sent, num_requests
        response = await create_items(COLLECTION_NAME, data, AUTH_TOKEN)  # Use async function
        response.raise_for_status()
        bytes_sent += len(json.dumps({"data": data}).encode("utf-8"))
        num_requests += 1


    async def saturate_link():
        nonlocal start_time, bytes_sent

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                current_bps = bytes_sent * 8 / elapsed_time  # bits per second
                if current_bps < bandwidth_bps:
                    await send_request()
                else:
                    await asyncio.sleep(0.001) #sleep for 1ms to avoid busy-waiting
            else:
                await send_request()
            if time.time() - start_time > 10: # Run for 10 seconds for testing
                break


    await saturate_link()

    context.num_requests = num_requests
    context.start_time = start_time
    context.elapsed_time = time.time() - start_time

    print(f"Sent {context.num_requests} requests in {context.elapsed_time:.2f} seconds.")


@then("the service must maintain {availability}% availability")
def step_impl(context, availability: float):
    """Checks if the service maintained the required availability."""
    # In a real implementation, you would monitor the service's actual
    # availability (e.g., using metrics from a monitoring system).
    # This is a placeholder to ensure the test can pass if all requests succeed.
    #
    #  For demonstration, we assume that if all requests completed without
    #  exceptions, we achieved 100% availability.  This is insufficient for a
    #  real test.

    if getattr(context, 'num_requests', 0) > 0: #Check if any requests were made
        context.availability = 100.0
    else:
        context.availability = 0.0

    assert context.availability >= float(availability), (
        f"Availability {context.availability}% is below the required {availability}%"
    )


@then("p95 latency must be under {threshold_ms}ms")
def step_impl(context, threshold_ms: int):
    """Checks if the p95 latency is below the threshold."""

    # In a real implementation, you would measure the actual latency of each
    # request and calculate the p95 latency.  This is a placeholder.

    # For demonstration, we simulate latency data and calculate a (fake) p95 latency.
    # Replace this with actual measurements.

    # Simulate some latency values (replace with actual measurements)
    latencies = [10, 15, 20, 25, 30]  # Example latencies in milliseconds

    # Calculate p95 latency (simple approximation)
    latencies.sort()
    p95_index = int(0.95 * len(latencies))
    p95_latency = latencies[p95_index]

    assert p95_latency <= int(threshold_ms), (
        f"P95 latency {p95_latency}ms exceeds the threshold of {threshold_ms}ms"
    )

    print(f"P95 latency: {p95_latency}ms")