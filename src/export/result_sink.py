import json
import os

class ResultSink:
    def write_from_spec(self, bench_spec: dict, report: dict) -> None:
        export_cfg = (bench_spec.get("export") or {})
        if export_cfg.get("console") is True:
            print(json.dumps(report, indent=2))

        json_cfg = (export_cfg.get("json") or {})
        path = json_cfg.get("path")
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        json_cfg = export_cfg.get("json", {})
        if json_cfg.get("enabled") is True and json_cfg.get("path"):
            path = json_cfg["path"]
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
