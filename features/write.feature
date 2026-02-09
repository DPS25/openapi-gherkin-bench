Feature: Data Ingestion Performance

  @ingestion @throughput
  Scenario Outline: Bandwidth-driven ingestion
    # Label: <profile_label>
    When I target the "write" operation
    And I saturate the link at <bandwidth> <unit>
    Then the service must maintain <availability>% availability
    And p95 latency must be under <threshold_ms>ms

    Examples:
      | profile_label | bandwidth | unit   | availability | threshold_ms |
      | light_load    | 10        | Mbit/s | 100.0        | 20           |
      | standard_load | 100       | Mbit/s | 99.9         | 50           |
      | stress_test   | 1000      | Mbit/s | 95.0         | 200          |