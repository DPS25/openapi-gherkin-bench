from behave import given, when, then
from pathlib import Path
import json
import re
import copy

try:
    import yaml
except ImportError as e:
    raise RuntimeError("Missing dependency: pyyaml") from e


_BOOL_TRUE = {"true", "1", "yes", "y", "on"}
_BOOL_FALSE = {"false", "0", "no", "n", "off"}


def _load_yaml(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"YAML file not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _write_yaml(path: str, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_json(path: str, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _coerce_scalar(v: str):
    s = str(v).strip()
    low = s.lower()

    if low in _BOOL_TRUE:
        return True
    if low in _BOOL_FALSE:
        return False

    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)

    if re.fullmatch(r"[+-]?\d+\.\d+", s):
        return float(s)

    return s


def _table_to_dict(table) -> dict:
    out = {}
    for row in table:
        key = row[0].strip()
        val = row[1].strip()
        out[key] = _coerce_scalar(val)
    return out


def _require_keys(obj: dict, keys: list[str], prefix: str):
    missing = [k for k in keys if k not in obj or obj[k] is None]
    if missing:
        raise AssertionError(f"Missing required {prefix} keys: {missing}")


def _ensure_benchmark_section(plan: dict, name: str) -> dict:
    bm = plan.setdefault("benchmarks", {}).setdefault(name, {})
    bm.setdefault("params", {})   
    bm.setdefault("intent", {})  
    return bm


@given('the universal benchmark base plan is loaded from "{plan_path}"')
def step_load_base_plan(context, plan_path):
    context.base_plan_path = plan_path
    context.base_plan = _load_yaml(plan_path)
    context.effective_plan = copy.deepcopy(context.base_plan)


@when('I benchmark a generic "{workflow}" workflow')
def step_set_generic_workflow(context, workflow):
    """
    We intentionally DO NOT require concrete operation IDs in the feature.
    The resolver (OpenAPI x-bdd + later Gemini) should pick suitable operations.
    """
    plan = copy.deepcopy(context.effective_plan)

    plan.setdefault("targets", {})
    plan["targets"]["workflow"] = str(workflow)

    plan["targets"]["write_operation_id"] = "auto"
    plan["targets"]["query_operation_id"] = "auto"

    plan["operations"] = [
        {"role": "write", "id": "auto"},
        {"role": "query", "id": "auto"},
    ]

    _ensure_benchmark_section(plan, "write")
    _ensure_benchmark_section(plan, "query")

    context.effective_plan = plan


@when("I configure runtime:")
def step_config_runtime(context):
    plan = copy.deepcopy(context.effective_plan)
    updates = _table_to_dict(context.table)

    plan["run"] = dict(updates)
    context.effective_plan = plan


@when("I describe ingestion intent:")
def step_config_ingestion_intent(context):
    plan = copy.deepcopy(context.effective_plan)
    updates = _table_to_dict(context.table)

    bm = _ensure_benchmark_section(plan, "write")
    bm["intent"].clear()
    bm["intent"].update(updates)

    context.effective_plan = plan


@when("I describe query intent:")
def step_config_query_intent(context):
    plan = copy.deepcopy(context.effective_plan)
    updates = _table_to_dict(context.table)

    bm = _ensure_benchmark_section(plan, "query")
    bm["intent"].clear()
    bm["intent"].update(updates)

    context.effective_plan = plan


@when("I configure export:")
def step_config_export(context):
    plan = copy.deepcopy(context.effective_plan)
    updates = _table_to_dict(context.table)

    export_cfg = {
        "console": updates.get("console"),
        "json": {
            "enabled": True,
            "path": updates.get("json"),
        },
        "influx": {
            "enabled": False
        }
    }

    plan["export"] = export_cfg
    context.effective_plan = plan


@when('I write the effective plan to "{out_path}"')
def step_write_effective_plan(context, out_path):
    _write_yaml(out_path, context.effective_plan)


@when("I execute the plan")
def step_execute_plan(context):
    plan = context.effective_plan

    _require_keys(plan, ["run", "export", "targets", "benchmarks"], "plan")
    _require_keys(plan["run"], ["warmup", "iterations", "concurrency", "seed"], "plan.run")

    _require_keys(plan["targets"], ["workflow"], "plan.targets")

    _require_keys(plan["benchmarks"], ["write", "query"], "plan.benchmarks")
    _require_keys(plan["benchmarks"]["write"], ["intent"], "plan.benchmarks.write")
    _require_keys(plan["benchmarks"]["query"], ["intent"], "plan.benchmarks.query")

    if not plan["export"].get("json", {}).get("path"):
        raise AssertionError("Missing export.json.path (must be set by feature)")

    result = {
        "ok": True,
        "status": "stub",
        "note": "PlanRunner not implemented yet. This JSON proves the plan compilation works.",
        "effective_plan": plan,
    }
    context.run_result = result
    _write_json(plan["export"]["json"]["path"], result)


@then("the plan configuration should be valid")
def step_validate_plan(context):
    plan = context.effective_plan

    _require_keys(plan, ["run", "targets", "export", "benchmarks"], "plan")
    _require_keys(plan["run"], ["warmup", "iterations", "concurrency", "seed"], "plan.run")
    _require_keys(plan["targets"], ["workflow"], "plan.targets")
    _require_keys(plan["benchmarks"], ["write", "query"], "plan.benchmarks")

    for k in ("warmup", "iterations", "concurrency", "seed"):
        v = plan["run"][k]
        if not isinstance(v, int) or v < 0:
            raise AssertionError(f"Invalid run.{k}: {v}")
    if plan["run"]["iterations"] <= 0:
        raise AssertionError("run.iterations must be > 0")

    write_intent = plan["benchmarks"]["write"].get("intent") or {}
    query_intent = plan["benchmarks"]["query"].get("intent") or {}

    if not write_intent:
        raise AssertionError("benchmarks.write.intent must not be empty")
    if not query_intent:
        raise AssertionError("benchmarks.query.intent must not be empty")


@then('the benchmark results should be available at "{json_path}"')
def step_results_exist(context, json_path):
    p = Path(json_path)
    if not p.exists():
        raise AssertionError(f"Expected results JSON not found at: {p}")
