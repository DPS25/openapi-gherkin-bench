from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
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
    Pure orchestrator. 
    It just starts the pipeline:

      1) Factory resolves SUT + OpenAPI (from feature + env)
      2) UniversalAdapter uses Gemini to generate a BenchmarkSpec (guardrailed)
      3) DataGenerator generates payload streams (based on spec + openapi + params)
      4) Execute warmup iterations, then measured iterations (as spec instructs)
    """

    def __init__(self, factory, universal_adapter, data_gen, result_sink) -> None:
        self.factory = factory
        self.ua = universal_adapter
        self.data_gen = data_gen
        self.sink = result_sink

    def run_from_feature(
        self,
        feature_path: str,
        scenario_name: str,
        gherkin_steps: List[Dict[str, str]],
        gherkin_docstrings: List[str],
    ) -> PlanRunnerResult:
        run_id = str(uuid.uuid4())
        created_at_ms = int(time.time() * 1000)

        feature_bundle = {
            "feature_path": feature_path,
            "scenario_name": scenario_name,
            "steps": gherkin_steps,          # list of {keyword,text}
            "docstrings": gherkin_docstrings # raw blocks (YAML/JSON/free text)
        }


        guardrails = self._guardrails_from_feature_bundle(feature_bundle)

        built = self.factory.build_from_feature(feature_bundle)
        system_id = built.get("system_id") or built.get("sut_id") or "unknown_system"
        sut = built.get("sut")
        if sut is None:
            raise RuntimeError("Factory.build_from_feature(...) must return typed 'sut' (SUTContext).")

        bench_spec = self.ua.create_benchmark_spec(
            run_id=run_id,
            feature_bundle=feature_bundle,
            factory_bundle=built,
            guardrails=guardrails,
        )

        payload_provider = self.data_gen.prepare(
            bench_spec=bench_spec,
            openapi=sut.openapi,
            sut=sut,
        )

        execution_report = self.ua.execute_spec(
            run_id=run_id,
            bench_spec=bench_spec,
            factory_bundle=built,
            payload_provider=payload_provider,
            guardrails=guardrails,
        )

        wrapped_report: Dict[str, Any] = {
            "ok": bool(execution_report.get("ok", True)),
            "run_id": run_id,
            "created_at_ms": created_at_ms,
            "system_id": system_id,
            "feature": feature_bundle,
            "guardrails": guardrails,
            "sut": {
                "base_url": sut.base_url,
                "openapi_path": sut.openapi_path,
                "meta": sut.sut_meta,
                "env": sut.env,
            },
            "benchmark_spec": bench_spec,
            "report": execution_report,
        }

        self.sink.write_from_spec(bench_spec, wrapped_report)

        return PlanRunnerResult(
            ok=wrapped_report["ok"],
            run_id=run_id,
            system_id=system_id,
            report=wrapped_report,
        )

    def _guardrails_from_feature_bundle(self, feature_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Steps file should only provide guardrails.
        Keep it conservative:
          - cap concurrency
          - cap iterations
          - cap payload size
          - forbid dangerous tools/commands in any LLM output
        Later: allow feature docstrings to override (still guardrailed).
        """
        return {
            "max_concurrency": 64,
            "max_iterations": 1_000_000,
            "max_payload_bytes": 2_000_000,
            "forbid_strings": ["rm -rf", "sudo ", "curl | sh", "powershell -enc"],
            "require_json_output": True,
        }
