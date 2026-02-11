import os, argparse, sys, yaml, time, json, re
from pathlib import Path
from google import genai


def setup_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not set.")
        sys.exit(1)
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1'})


_REF_RE = re.compile(r'"\\$ref"\\s*:\\s*"([^"]+)"')


def _collect_refs(obj) -> set[str]:
    """
    Collect all $ref values inside an object.
    Uses a JSON string scan for speed + robustness.
    """
    try:
        blob = json.dumps(obj)
    except Exception:
        blob = str(obj)
    return set(_REF_RE.findall(blob))


def _parse_ref(ref: str):
    """
    Support both:
      - #/components/schemas/Foo (OpenAPI3)
      - #/definitions/Bar       (Swagger2)
    Returns tuple(kind, name) where kind in {"schema", "definition"}.
    """
    if ref.startswith("#/components/schemas/"):
        return ("schema", ref.split("/", 3)[3])
    if ref.startswith("#/definitions/"):
        return ("definition", ref.split("/", 2)[2])
    return (None, None)


def extract_minimal_spec(spec_path, target_op_id):
    """
    Parses the spec and returns only the relevant operation + referenced schemas/definitions.
    Supports OpenAPI 3.x and Swagger 2.0 (Alertmanager).
    """
    with open(spec_path, 'r') as f:
        full_spec = yaml.safe_load(f)

    is_swagger2 = isinstance(full_spec.get("swagger"), str) and full_spec["swagger"].startswith("2.")
    is_openapi3 = isinstance(full_spec.get("openapi"), str) and full_spec["openapi"].startswith("3.")

    if not (is_swagger2 or is_openapi3):
        # Heuristic fallback
        is_swagger2 = "definitions" in full_spec and "paths" in full_spec
        is_openapi3 = "components" in full_spec and "paths" in full_spec

    if is_swagger2:
        minimal_spec = {
            "swagger": full_spec.get("swagger", "2.0"),
            "info": full_spec.get("info", {}),
            "host": full_spec.get("host"),
            "basePath": full_spec.get("basePath", ""),
            "schemes": full_spec.get("schemes"),
            "consumes": full_spec.get("consumes"),
            "produces": full_spec.get("produces"),
            "paths": {},
            "definitions": {}
        }
        # optional security, if present
        if "securityDefinitions" in full_spec:
            minimal_spec["securityDefinitions"] = full_spec["securityDefinitions"]
        if "security" in full_spec:
            minimal_spec["security"] = full_spec["security"]

        defs = full_spec.get("definitions", {}) or {}

    else:
        minimal_spec = {
            "openapi": full_spec.get("openapi", "3.0.0"),
            "info": full_spec.get("info", {}),
            "servers": full_spec.get("servers"),
            "paths": {},
            "components": {"schemas": {}}
        }
        if "security" in full_spec:
            minimal_spec["security"] = full_spec["security"]
        if "components" in full_spec and isinstance(full_spec["components"], dict):
            if "securitySchemes" in full_spec["components"]:
                minimal_spec["components"]["securitySchemes"] = full_spec["components"]["securitySchemes"]

        schemas = (full_spec.get("components", {}) or {}).get("schemas", {}) or {}

    found = False
    op_details = None

    # 1) Find the operation by operationId
    for path, methods in (full_spec.get("paths", {}) or {}).items():
        if not isinstance(methods, dict):
            continue

        kept_methods = {}
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            if details.get("operationId") == target_op_id:
                kept_methods[method] = details
                op_details = details
                found = True
                break

        if kept_methods:
            minimal_spec["paths"][path] = kept_methods
            break

    if not found or not op_details:
        print(f"⚠️ Warning: operationId '{target_op_id}' not found in spec. Sending small sample instead.")
        return f"Operation {target_op_id} not found."

    # 2) Collect refs from the operation and pull in referenced schemas/definitions transitively
    refs = set()
    refs |= _collect_refs(op_details)

    # Also consider params/responses (Swagger2 sometimes uses top-level refs)
    # Keep them minimal if present:
    if is_swagger2:
        if "parameters" in full_spec and isinstance(full_spec["parameters"], dict):
            minimal_spec["parameters"] = full_spec["parameters"]
            refs |= _collect_refs(full_spec["parameters"])
        if "responses" in full_spec and isinstance(full_spec["responses"], dict):
            minimal_spec["responses"] = full_spec["responses"]
            refs |= _collect_refs(full_spec["responses"])

        changed = True
        while changed:
            changed = False
            for r in list(refs):
                kind, name = _parse_ref(r)
                if kind == "definition" and name in defs and name not in minimal_spec["definitions"]:
                    minimal_spec["definitions"][name] = defs[name]
                    new_refs = _collect_refs(defs[name])
                    if not new_refs.issubset(refs):
                        refs |= new_refs
                        changed = True
    else:
        changed = True
        while changed:
            changed = False
            for r in list(refs):
                kind, name = _parse_ref(r)
                if kind == "schema" and name in schemas and name not in minimal_spec["components"]["schemas"]:
                    minimal_spec["components"]["schemas"][name] = schemas[name]
                    new_refs = _collect_refs(schemas[name])
                    if not new_refs.issubset(refs):
                        refs |= new_refs
                        changed = True

    return yaml.dump(minimal_spec, sort_keys=False)


def generate_benchmark():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["write", "query", "delete"])
    parser.add_argument("service")
    args = parser.parse_args()

    # Load Mapping
    with open("mapping.yaml", "r") as f:
        config = yaml.safe_load(f)

    svc_cfg = config.get(args.service)
    op_id = svc_cfg["operations"][args.operation]["operationId"]
    spec_path = Path(svc_cfg["spec_path"])

    print(f"🔍 Extracting {op_id} from {spec_path}...")
    relevant_spec = extract_minimal_spec(spec_path, op_id)

    feature_text = Path(f"features/{args.operation}.feature").read_text()
    client = setup_client()

    prompt = f"""
    TASK: Generate Behave steps for {args.service}.
    RELEVANT API SPEC:
    {relevant_spec}

    GHERKIN FEATURE:
    {feature_text}

    REQUIREMENTS:
    - Use httpx and asyncio
    - IMPORTANT: Build URLs correctly:
    - If Swagger2, respect basePath (e.g. /api/v2)
    - If OpenAPI3, respect servers if present
    - Match the spec schemas/definitions
    - Output ONLY raw python code (no markdown fences)
    """

    # Retry logic for 429s
    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)

            out_dir = Path("services") / args.service
            out_dir.mkdir(parents=True, exist_ok=True)
            output_file = out_dir / f"{args.operation}.py"

            clean_code = response.text.strip()
            clean_code = clean_code.removeprefix("```python").removesuffix("```").strip()
            output_file.write_text(clean_code)
            print(f"✨ Created: {output_file}")
            break
        except Exception as e:
            if "429" in str(e):
                print(f"😴 Rate limited. Waiting {30 * (attempt + 1)}s...")
                time.sleep(30 * (attempt + 1))
            else:
                print(f"❌ Error: {e}")
                break


if __name__ == "__main__":
    generate_benchmark()
