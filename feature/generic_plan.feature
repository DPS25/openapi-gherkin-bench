@universal
Feature: Universal Benchmark Plan (intent-driven)
  The runner must remain SUT-agnostic.
  This feature describes WHAT should be benchmarked (intent), not HOW a specific SUT performs it.
  System-specific parameter mapping + request shaping is delegated to the OpenAPI x-bdd metadata
  and (later) the Gemini integration.

  Background:
    Given the universal benchmark base plan is loaded from "specs/benchmarks/universal.yaml"

  Scenario Outline: Universal ingest + query benchmark - <profile>
    When I benchmark a generic "write_then_query" workflow

    And I configure runtime:
      | warmup      | <warmup>      |
      | iterations  | <iterations>  |
      | concurrency | <concurrency> |
      | seed        | <seed>        |

    And I describe ingestion intent:
      | volume | <ingest_volume> |
      | unit   | <ingest_unit>   |
      | shape  | <data_shape>    |
      | order  | <time_order>    |

    And I describe query intent:
      | kind       | <query_kind>  |
      | time_range | <time_range>  |
      | expectation| <expectation> |

    And I configure export:
      | console | <console> |
      | json    | <jsonPath> |

    And I write the effective plan to "<effectivePlanPath>"

    When I execute the plan
    Then the plan configuration should be valid
    And the benchmark results should be available at "<jsonPath>"

    @normal
    Examples:
      | profile | warmup | iterations | concurrency | seed | ingest_volume | ingest_unit | data_shape | time_order | query_kind | time_range | expectation | console | jsonPath               | effectivePlanPath               |
      | smoke   | 5      | 20         | 1           | 42   | 10            | MB          | simple     | in_order   | range      | 10m        | non_empty   | true    | results/universal.json | results/effective_universal.yml |
      | avg     | 10     | 50         | 2           | 42   | 250           | MB          | medium     | in_order   | aggregate  | 1h         | non_empty   | true    | results/universal.json | results/effective_universal.yml |
      | stress  | 10     | 80         | 4           | 42   | 1             | GB          | medium     | in_order   | aggregate  | 6h         | non_empty   | true    | results/universal.json | results/effective_universal.yml |
