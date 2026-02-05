from behave import given, when, then
from pathlib import Path
import json
import re

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


def _require(obj, path: str):
    """
    Ensure nested dict path exists: e.g. _require(plan, "benchmarks.write.params")
    """
    parts = path.split(".")
    cur = obj
    for p in parts:
        if p not in cur or cur[p] is None:
            cur[p] = {}
        cur = cur[p]
    return cur


def _require_keys(obj: dict, keys: list[str], prefix: str):
    missing = [k for k in keys if k not in obj or obj[k] is None]
    if missing:
        raise AssertionError(f"Missing required {prefix} keys: {missing}")


@given('the universal benchmark base plan is loaded from "{plan_path}"')
def step_load_base_plan(context, plan_path):
    context.base_plan_path = plan_path
    context.base_plan = _load_yaml(plan_path)
    context.effective_plan = dict(context.base_plan)


@when('I benchmark write operation "{write_operation_id}" and query operation "{query_operation_id}"')
def step_set_targets(context, write_operation_id, query_operation_id):
    plan = dict(context.effective_plan)

    plan.setdefault("targets", {})
    plan["targets"]["write_operation_id"] = str(write_operation_id)
    plan["targets"]["query_operation_id"] = str(query_operation_id)

    plan["operations"] = [
        {"role": "write", "id": str(write_operation_id)},
        {"role": "query", "id": str(query_operation_id)},
    ]

    context.effective_plan = plan


@when("I configure runtime:")
def step_config_runtime(context):
    plan = dict(context.effective_plan)
    updates = _table_to_dict(context.table)

    plan["run"] = dict(updates)
    context.effective_plan = plan


@when("I configure write parameters:")
def step_config_write(context):
    plan = dict(context.effective_plan)
    updates = _table_to_dict(context.table)

    params = _require(plan, "benchmarks.write.params")
    params.clear()
    params.update(updates)

    context.effective_plan = plan


@when("I configure query parameters:")
def step_config_query(context):
    plan = dict(context.effective_plan)
    updates = _table_to_dict(context.table)

    params = _require(plan, "benchmarks.query.params")
    params.clear()
    params.update(updates)

    context.effective_plan = plan


@when("I configure export:")
def step_config_export(context):
    plan = dict(context.effective_plan)
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

    _require_keys(plan, ["run", "export", "targets"], "plan")
    _require_keys(plan["run"], ["warmup", "iterations", "concurrency", "seed"], "plan.run")
    _require_keys(plan["targets"], ["write_operation_id", "query_operation_id"], "plan.targets")

    _require_keys(plan.get("benchmarks", {}), ["write", "query"], "plan.benchmarks")
    _require_keys(plan["benchmarks"]["write"], ["params"], "plan.benchmarks.write")
    _require_keys(plan["benchmarks"]["query"], ["params"], "plan.benchmarks.query")

    if not plan["export"].get("json", {}).get("path"):
        raise AssertionError("Missing export.json.path (must be set by feature)")

    # ---- REAL EXECUTION (later) ---------------------------------
    # from src.bench.plan_runner import PlanRunner
    # result = PlanRunner().run(plan)
    # context.run_result = result
    # --------------------------------------------------------------

    result = {"ok": True, "status": "stub", "note": "PlanRunner not implemented yet.", "plan": plan}
    context.run_result = result

    _write_json(plan["export"]["json"]["path"], result)


@then("the plan configuration should be valid")
def step_validate_plan(context):
    plan = context.effective_plan

    _require_keys(plan, ["run", "targets", "export", "benchmarks"], "plan")
    _require_keys(plan["run"], ["warmup", "iterations", "concurrency", "seed"], "plan.run")
    _require_keys(plan["targets"], ["write_operation_id", "query_operation_id"], "plan.targets")

    for k in ("warmup", "iterations", "concurrency", "seed"):
        v = plan["run"][k]
        if not isinstance(v, int) or v < 0:
            raise AssertionError(f"Invalid run.{k}: {v}")
    if plan["run"]["iterations"] <= 0:
        raise AssertionError("run.iterations must be > 0")
    if plan["run"]["concurrency"] <= 0:
        raise AssertionError("run.concurrency must be > 0")

    if not plan["export"].get("json", {}).get("path"):
        raise AssertionError("export.json.path must be set (export step)")

    if not isinstance(plan["benchmarks"]["write"].get("params"), dict):
        raise AssertionError("benchmarks.write.params must be a dict")
    if not isinstance(plan["benchmarks"]["query"].get("params"), dict):
        raise AssertionError("benchmarks.query.params must be a dict")


@then('the benchmark results should be available at "{json_path}"')
def step_results_exist(context, json_path):
    p = Path(json_path)
    if not p.exists():
        raise AssertionError(f"Expected results file to exist: {p}")
    json.loads(p.read_text(encoding="utf-8"))
