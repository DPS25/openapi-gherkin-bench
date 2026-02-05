from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import json
import os
import time
import uuid


@dataclass
class PlanRunnerResult:
    ok: bool
    run_id: str
    system_id: str
    report: Dict[str, Any]


class PlanRunner:
    """
    PlanRunner is an orchestrator:
      - reads the effective universal plan (already filled by Behave steps)
      - asks Factory to select the SUT via ENVs and load its OpenAPI spec + metadata
      - builds a 'system_dictionary' that UA/Gemini can use to create the system-specific benchmark
      - delegates execution to UniversalAdapter (UA does health check + Gemini + benchmark execution)
      - exports the final report (JSON + optional console)
    """

    def __init__(self, factory, universal_adapter) -> None:
        """
        factory: must expose build(plan) -> dict with keys:
            - system_id (str)
            - openapi (dict)
            - sut_meta (dict)          
            - env (dict)              
            - openapi_path (str)      
        universal_adapter: must expose run(system_dict) -> dict report
        """
        self.factory = factory
        self.ua = universal_adapter

    def run(self, plan: Dict[str, Any]) -> PlanRunnerResult:
        self._validate_plan_minimal(plan)

        run_id = str(uuid.uuid4())
        created_at_ms = int(time.time() * 1000)

        f = self.factory.build(plan)
        system_id = f.get("system_id") or f.get("sut_id")  
        if not system_id:
            raise RuntimeError("Factory.build(plan) must return system_id/sut_id")

        openapi = f.get("openapi")
        if not isinstance(openapi, dict):
            raise RuntimeError("Factory.build(plan) must return openapi dict")

        sut_meta = f.get("sut_meta") or {}
        env = f.get("env") or {}
        openapi_path = f.get("openapi_path")

        system_dict: Dict[str, Any] = {
            "run_id": run_id,
            "created_at_ms": created_at_ms,

            "plan": plan,

            "system": {
                "id": system_id,
                "openapi_path": openapi_path,
                "meta": sut_meta,   
                "env": env,         
                "openapi": openapi, 
            },

            "workflow": (plan.get("targets") or {}).get("workflow"),
            "run": plan.get("run", {}),
            "benchmarks": plan.get("benchmarks", {}),
        }

        report = self.ua.run(system_dict)

        wrapped_report = {
            "ok": bool(report.get("ok", True)),
            "run_id": run_id,
            "system_id": system_id,
            "sut": {
                "id": sut_meta.get("id") or system_id,
                "version": sut_meta.get("version"),
                "base_url": sut_meta.get("base_url") or env.get("SUT_BASE_URL") or env.get("base_url"),
            },
            "plan": {
                "run": plan.get("run", {}),
                "targets": plan.get("targets", {}),
                "benchmarks": plan.get("benchmarks", {}),
                "export": plan.get("export", {}),
                "meta": plan.get("meta", {}),
            },
            "report": report,
        }

        self._export(plan, wrapped_report)

        return PlanRunnerResult(
            ok=wrapped_report["ok"],
            run_id=run_id,
            system_id=system_id,
            report=wrapped_report,
        )

    # ----------------------------
    # Validation + export
    # ----------------------------

    def _validate_plan_minimal(self, plan: Dict[str, Any]) -> None:
        if not isinstance(plan, dict):
            raise ValueError("plan must be a dict")

        run = plan.get("run") or {}
        for k in ("warmup", "iterations", "concurrency", "seed"):
            if run.get(k, None) is None:
                raise ValueError(f"plan.run.{k} must be set (from Gherkin)")

        targets = plan.get("targets") or {}
        if targets.get("workflow", None) is None:
            raise ValueError("plan.targets.workflow must be set (from Gherkin)")

        bms = plan.get("benchmarks") or {}
        if "write" not in bms or "query" not in bms:
            raise ValueError("plan.benchmarks must include write and query")

        export_cfg = plan.get("export") or {}
        json_cfg = export_cfg.get("json") or {}
        if not json_cfg.get("path"):
            raise ValueError("plan.export.json.path must be set (from Gherkin)")

    def _export(self, plan: Dict[str, Any], report: Dict[str, Any]) -> None:
        export_cfg = plan.get("export") or {}

        if export_cfg.get("console") is True:
            print(json.dumps(report, indent=2))

        json_cfg = export_cfg.get("json") or {}
        if json_cfg.get("enabled") is True and json_cfg.get("path"):
            path = str(json_cfg["path"])
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
