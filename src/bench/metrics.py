import statistics

class Metrics:
    def aggregate(self, events: list[dict]) -> dict:
        # events: [{role, phase, status, duration_ms, bytes, ok, error?}, ...]
        # compute per (phase, role): count, ok, err, p50/p95, bytes_total
        return {
            "by_phase_role": {},
            "summary": {}
        }
