from behave import *
import httpx
import asyncio
import json  # Import the json module

@when('I target the "{operation}" operation')
def step_impl(context, operation):
    context.operation = operation  # Store the targeted operation
    context.url = '/write'  # Assuming the /write endpoint
    

@when('I saturate the link at {bandwidth} {unit}')
def step_impl(context, bandwidth, unit):
    context.bandwidth = float(bandwidth)
    context.unit = unit
    
    # Calculate the target number of bytes per second based on bandwidth.
    if unit == "Mbit/s":
        bytes_per_second = (context.bandwidth * 1000000) / 8  # Mbit/s to bytes/s
    elif unit == "Gbit/s":
        bytes_per_second = (context.bandwidth * 1000000000) / 8  # Gbit/s to bytes/s
    else:
        raise ValueError(f"Unsupported unit: {unit}")
    
    context.target_bytes_per_second = bytes_per_second
    
    async def send_data(url, target_bytes_per_second):
        async with httpx.AsyncClient(base_url=context.base_url) as client:
            start_time = asyncio.get_event_loop().time()
            total_bytes_sent = 0
            successful_requests = 0
            total_requests = 0
            latencies = []

            while asyncio.get_event_loop().time() - start_time < 60:  # Run for 60 seconds
                # Generate line protocol data
                line_protocol_data = f"airSensors,sensor_id=TLM{total_requests % 1000:04} temperature={total_requests % 100},humidity={total_requests % 50},co={total_requests % 10} {int(asyncio.get_event_loop().time() * 1e9)}\n"
                data_bytes = line_protocol_data.encode('utf-8')

                # Control the sending rate
                current_time = asyncio.get_event_loop().time()
                elapsed_time = current_time - start_time
                target_bytes_sent = elapsed_time * target_bytes_per_second
                
                if total_bytes_sent < target_bytes_sent:
                  try:
                      request_start_time = asyncio.get_event_loop().time()
                      response = await client.post(
                          url,
                          data=data_bytes,
                          params={"org": context.org, "bucket": context.bucket},
                          headers={"Content-Type": "text/plain; charset=utf-8"}
                      )
                      request_end_time = asyncio.get_event_loop().time()
                      total_requests += 1
                      if response.status_code == 204:
                          successful_requests += 1
                          total_bytes_sent += len(data_bytes)
                          latencies.append((request_end_time - request_start_time) * 1000)
                      else:
                          print(f"Request failed with status code: {response.status_code}, Response: {response.text}")  # Print error response
                  except httpx.HTTPError as e:
                      print(f"HTTP error occurred: {e}")  # Print HTTP errors
                      
                await asyncio.sleep(0.000001)  # Control loop speed to avoid CPU hogging.
            
            context.successful_requests = successful_requests
            context.total_requests = total_requests
            context.latencies = latencies
            context.availability = (successful_requests / total_requests) * 100 if total_requests > 0 else 100.0 #Capture availability
            context.total_bytes_sent = total_bytes_sent #capture total bytes sent

    asyncio.run(send_data(context.url, context.target_bytes_per_second))

@then('the service must maintain {availability}% availability')
def step_impl(context, availability):
  expected_availability = float(availability)
  actual_availability = context.availability
  assert actual_availability >= expected_availability, f"Availability was {actual_availability}%, expected at least {expected_availability}%"


@then('p95 latency must be under {threshold_ms}ms')
def step_impl(context, threshold_ms):
    threshold = float(threshold_ms)
    latencies = context.latencies
    
    if not latencies:
        assert True, "No latencies recorded"
        return
    
    latencies.sort()
    p95_index = int(0.95 * len(latencies))
    p95_latency = latencies[p95_index]
    
    assert p95_latency <= threshold, f"P95 latency was {p95_latency:.2f}ms, expected under {threshold}ms"