class UniversalAdapter:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini
        self.metrics = Metrics()
        self.asserts = AssertEngine()

    def create_benchmark_spec(self, run_id: str, feature_bundle: dict, factory_bundle: dict, guardrails: dict) -> dict:
        system_dict = {
            "run_id": run_id,
            "feature": feature_bundle,
            "sut": {
                "openapi": factory_bundle.get("openapi"),
                "meta": factory_bundle.get("sut_meta"),
                "env": factory_bundle.get("env"),
                "base_url": factory_bundle.get("sut").base_url,
            },
            "guardrails": guardrails,
        }
        prompt = "..."  
        spec = self.gemini.generate_benchmark_skeleton(prompt, system_dict)

        # TODO: validate spec vs guardrails + schema
        return spec

    def execute_spec(self, run_id: str, bench_spec: dict, factory_bundle: dict, payload_provider, guardrails: dict) -> dict:
        # TODO: implement events, metrics, assertions (generic)
        return {"ok": True, "events": [], "metrics": {}, "assertions": {}}

    def run(self, job: UniversalJob, data_gen: DataGenerator) -> dict:
        sut = job.sut

        self.health_check(sut)

        op_catalog = self.discover_operations(sut.openapi)
        system_dict = {
            "run_id": job.run_id,
            "plan": job.plan,
            "sut": {
                "base_url": sut.base_url,
                "openapi": sut.openapi,
                "meta": sut.sut_meta,
                "env": sut.env,
            },
            "phases": [p.__dict__ for p in job.phases],
            "operation_order": job.operation_order,
            "discovered_ops": op_catalog,
        }

        prompt = build_benchmark_prompt(system_dict)
        bench_plan = self.gemini.generate_benchmark_skeleton(prompt, system_dict)

        events = self.execute_benchmark_plan(job, bench_plan, data_gen)
        metrics = self.metrics.aggregate(events)
        assertions = self.asserts.run(job.plan, metrics, events)

        return {
            "ok": bool(assertions.get("ok", True)),
            "benchmark_plan": bench_plan,
            "metrics": metrics,
            "assertions": assertions,
            "events_sample": events[:50],
        }
