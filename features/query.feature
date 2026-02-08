Feature: Data Retrieval Performance

  @retrieval @concurrency
  Scenario Outline: Scalable query execution
    # Label: <profile_label>
    When I target the "query" operation
    And I simulate <concurrency> concurrent users
    Then the response status should be 200
    And the <metric> response time should be under <limit_ms>ms

    Examples:
      | profile_label | concurrency | metric | limit_ms |
      | baseline      | 10          | mean   | 50       |
      | moderate      | 100         | p95    | 150      |
      | high_density  | 500         | p99    | 500      |