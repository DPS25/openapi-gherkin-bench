@universal
Feature: Universal Benchmark Plan (write + query)
  The runner must remain SUT-agnostic.
  Health checks are handled internally by the Universal Adapter and are NOT benchmark operations here.

  Background:
    Given the universal benchmark base plan is loaded from "specs/benchmarks/universal.yaml"

  Scenario Outline: Universal write + query benchmark - <profile>
    When I benchmark write operation "<write_operation_id>" and query operation "<query_operation_id>"

    And I configure runtime:
      | warmup      | <warmup>      |
      | iterations  | <iterations>  |
      | concurrency | <concurrency> |
      | seed        | <seed>        |

    And I configure write parameters:
      | batch_size        | <batch_size>        |
      | parallel_writers  | <parallel_writers>  |
      | batches           | <batches>           |
      | write_compression | <write_compression> |
      | precision         | <precision>         |
      | point_complexity  | <point_complexity>  |
      | tag_cardinality   | <tag_cardinality>   |
      | time_ordering     | <time_ordering>     |
      | expected_points   | <expected_total_points> |

    And I configure query parameters:
      | time_range         | <time_range>         |
      | query_type         | <query_type>         |
      | result_size        | <result_size>        |
      | concurrent_clients | <concurrent_clients> |
      | query_repeats      | <query_repeats>      |
      | output_format      | <output_format>      |
      | query_compression  | <query_compression>  |

    And I configure export:
      | console | <console> |
      | json    | <jsonPath> |

    And I write the effective plan to "<effectivePlanPath>"

    When I execute the plan
    Then the plan configuration should be valid
    And the benchmark results should be available at "<jsonPath>"

    @normal
    Examples:
      | profile | write_operation_id | query_operation_id | warmup | iterations | concurrency | seed | batch_size | parallel_writers | batches | expected_total_points | write_compression | precision | point_complexity | tag_cardinality | time_ordering | time_range | query_type  | result_size | concurrent_clients | query_repeats | output_format | query_compression | console | jsonPath               | effectivePlanPath               |
      | smoke   | ingest_batch       | query_range        | 10     | 50         | 1           | 42   | 100        | 1                | 10      | 1000                  | none              | ns        | low              | 10              | in_order      | 10s        | filter      | small       | 1                  | 1             | csv           | none              | true    | results/universal.json | results/effective_universal.yml |
      | average | ingest_batch       | query_range        | 10     | 50         | 1           | 42   | 250        | 2                | 10      | 5000                  | none              | ns        | medium           | 100             | in_order      | 1h         | aggregate   | small       | 2                  | 2             | csv           | gzip              | true    | results/universal.json | results/effective_universal.yml |
      | stress  | ingest_batch       | query_range        | 10     | 50         | 1           | 42   | 500        | 2                | 20      | 20000                 | none              | ns        | medium           | 250             | in_order      | 6h         | aggregate   | large       | 4                  | 2             | csv           | gzip              | true    | results/universal.json | results/effective_universal.yml |
      | spike   | ingest_batch       | query_range        | 10     | 50         | 1           | 42   | 250        | 4                | 10      | 10000                 | none              | ns        | medium           | 250             | in_order      | 1h         | filter      | large       | 8                  | 1             | csv           | gzip              | true    | results/universal.json | results/effective_universal.yml |
      | break   | ingest_batch       | query_range        | 10     | 50         | 1           | 42   | 1000       | 4                | 25      | 100000                | none              | ns        | high             | 500             | in_order      | 1h         | aggregate   | large       | 8                  | 1             | csv           | gzip              | true    | results/universal.json | results/effective_universal.yml |
      | soak    | ingest_batch       | query_range        | 10     | 50         | 1           | 42   | 100        | 1                | 300     | 30000                 | none              | ns        | low              | 100             | in_order      | 72h        | filter      | small       | 2                  | 5             | csv           | none              | true    | results/universal.json | results/effective_universal.yml | 
