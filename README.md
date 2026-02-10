
## 🚀 Adding & Activating a Service

Follow these steps to integrate a new service while keeping the project structure clean.

### 1. Register the Service

Add the service path and the specific `operationId` mappings to your root `mapping.yaml`.

```yaml
# mapping.yaml
my-new-service:
  spec_path: "vendor/my-service/openapi.yaml"
  operations:
    write: 
      operationId: "IngestMetrics"

```

### 2. Generate the Step File

Run the `generate.py` script. Based on our latest version, this will extract only the relevant portion of the OpenAPI spec and save the Python code to a dedicated service folder.

```bash
python generate.py write my-new-service

```

* **Output Location:** `services/my-new-service/write.py`

### 3. Activate the Service (The `ln` Step)

Because **Behave** strictly looks for a folder named `steps` inside your `features` directory, you must point that folder to your new service's code.

```bash
# Link features/steps to your specific service library
ln -sfn ../services/my-new-service features/steps

```

> **Tip:** The `../services/...` path is relative to the `features/` directory where the link sits.

### 4. Run the Benchmark

Now that the link is active, Behave will "see" the Python steps for your new service as if they were natively in the `features/steps` folder.

```bash
export ENV_NAME=<ENV-NAME>  && nix develop
behave --tags=@ingestion

```

---

## 📂 Project Structure Overview

After following this workflow, your directory tree looks like this:

```text
.
├── mapping.yaml
├── generate.py
├── features/
│   ├── write.feature
│   └── steps              # 🔗 SYMLINK -> ../services/my-new-service
├── services/
│   ├── influx-openapi/
│   │   └── write.py       # (Inactive)
│   └── my-new-service/
│       └── write.py       # (Active via link)
└── vendor/
    └── my-service/
        └── openapi.yaml

```

---
## Implemented services 

### InfluxDB

- **What does it do?**
  - Time-series database (TSDB) for storing and querying metrics/events via a well-defined HTTP API.

- **Why did we choose it?**
  - Baseline TSDB in our benchmark suite (clear ingest/query/delete semantics).
  - Comes with an upstream OpenAPI contract repo vendored as a submodule (`vendor/influx-openapi/...`), which fits our `generate.py + Gemini` workflow.

- **Potential problems**

### Prometheus (Server)

- **What does it do?**
  - Metrics/monitoring TSDB with PromQL query API; can accept data via Remote Write (if enabled).

- **Why did we choose it?**
  - Widely used OSS standard → expands our TSDB service range.
  - Strong “read/query” benchmarking via `query_range` (concurrency, p95/p99, etc.).

- **Potential problems**
  - No upstream, versioned OpenAPI contract like InfluxDB → we maintain a small “benchmark subset” OpenAPI spec to keep the Gemini generation flow working.
  - Write endpoint is **Remote Write (protobuf + snappy)**, not plain text; invalid payloads can produce `400` and skew availability/latency.


### Alertmanager

- **What does it do?**
  - Alert processing service (dedup/group/routing) with an HTTP API for alerts and silences.

- **Why did we choose it?**
  - Has an upstream OpenAPI/Swagger spec in the official repo → we can vendor it as a submodule (same pattern as Influx).
  - Adds another well-defined API SUT to validate our benchmark pipeline (availability/latency/concurrency).

- **Potential problems**
  - Not a TSDB: “query” is alert-state reads, not time-series queries → not directly comparable to TSDB query benchmarks.
  - “Delete” is management/control-plane (e.g., silences), not time-series data deletion.
  - Realism depends on having enough generated alerts/silences; otherwise endpoints may return near-empty results.


---

## 🛠 Switching Services

To switch from `my-new-service` back to `influx-openapi`, you only need to run the `ln` command again:

```bash
# Switch back to InfluxDB
ln -sfn ../services/influx-openapi features/steps

# Verify the link
ls -l features/steps

```

Would you like me to provide a **shell alias** or a tiny **`activate.sh`** script that you can use to switch between services even faster (e.g., `./activate.sh influx-openapi`)?

## Universal Benchmark Flow

```mermaid
flowchart TD
  A["Gherkin Feature\n features/generic_plan.feature (@universal)"] --> B["Behave Runner"]
  B --> C["Steps (pseudocode)\n features/steps/generic_plan_steps.md"]

  C --> P1["load universal plan\n specs/benchmarks/universal.yaml"]
  C --> PR["Plan_Runner\n src/bench/plan_runner.md"]

  PR --> FCT["SUT Factory\n src/sut/factory.md"]
  FCT --> SPEC["OpenAPI Spec\n specs/systems/**/openapi.yaml"]
  FCT --> UA["Universal_Adapter\n src/sut/adapters/universal_adapter.md"]

  UA --> HCHK["Ping / Health\n/health or first GET"]
  UA --> DISC["Discovery\nfind x-bdd.operation"]

  PR --> DG["DataGenerator\n src/bench/data_gen.md"]
  DG --> PAY["Payload from Schema\n example -> default -> enum -> null"]

  PR --> WU["Warmup\n iterations x concurrency"]
  PR --> RUN["Run\n iterations x concurrency"]

  WU --> UA
  RUN --> UA
  UA --> RESP["HTTP Response\n status, body, height, duration"]

  RUN --> MET["Metrics\n src/bench/metrics.md"]
  MET --> AST["Assertions\n src/bench/assert_engine.md"]
  AST --> EXP["Results_Sink\n src/export/result_sink.md"]

  EXP --> OUT1["Console"]
  EXP --> OUT2["JSON\n results/universal.json"]
  EXP -.-> OUT3["Main Influx (optional)"]

  subgraph SPECS["Specs (nur Dateien)"]
    direction TB
    S1["universal plan\n specs/benchmarks/universal.yaml"] --> S5

    subgraph S2["Systeme"]
      direction TB
      S3["InfluxDB v2\n specs/systems/influxdb/v2/openapi.yaml"]
      S4["TSDB v1\n specs/systems/tsdb/v1/openapi.yaml"]
    end

    S5["Vorlage\n specs/templates/openapi-skeleton.yaml"]
  end

  subgraph OAPI["OpenAPI Vertrag"]
    direction TB
    O1["Root: x-bdd.sut\nid, version, defaults"]
    O2["Operationen: x-bdd.operation\nz.B. ingest_batch, query_range, health_check"]
    O3["Request-Schema\n examples/defaults for body and params"]
  end

  SPEC -. contains .-> OAPI
  DISC -. reads .-> O2
  DG -. uses .-> O3

  subgraph ENV["ENV Overrides"]
    direction TB
    E1["SUT_ID (z.B. vendor/service@vX)"]
    E2["SUT_BASE_URL"]
    E3["SUT_AUTH_TOKEN"]
    E4["SUT_SECURITY_SCHEME"]
  end

  ENV -. controles .-> FCT
  ENV -. Auth/URL .-> UA
```




