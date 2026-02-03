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
