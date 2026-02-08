Feature: Data Cleanup Performance

  @maintenance @cleanup
  Scenario Outline: Mass deletion cycles
    # Label: <profile_label>
    When I target the "delete" operation
    And I execute <batch_count> sequential batches
    Then the operation must complete within <timeout>s
    And the service must return status <status_code>

    Examples:
      | profile_label | batch_count | timeout | status_code |
      | single_purge  | 1           | 1       | 204         |
      | bulk_cleanup  | 50          | 10      | 204         |