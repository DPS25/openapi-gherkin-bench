GEMINI_OUTPUT_REQUIRED_KEYS = [
  "resolved_operation_mapping",
  "execution_steps",
]

# Example structure:
# resolved_operation_mapping: {
#   "write": {"method":"POST","path":"/api/v2/write", "headers":{...}, "query":{...}, "body_schema":"..."},
#   "query": {"method":"POST","path":"/api/v2/query", ...}
# }
# execution_steps: [
#   {"phase":"warmup", "iterations":10, "concurrency":2, "role":"write", "payload":"DATA_GEN:write"},
#   {"phase":"warmup", ... "role":"query", "payload":"DATA_GEN:query"},
#   {"phase":"run", ...}
# ]
