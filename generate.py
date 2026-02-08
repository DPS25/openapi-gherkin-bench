import os, argparse, sys, yaml, time
from pathlib import Path
from google import genai


def setup_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not set.")
        sys.exit(1)
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1'})


def extract_minimal_spec(spec_path, target_op_id):
    """Parses the large spec and returns only the relevant operation and its schemas."""
    with open(spec_path, 'r') as f:
        full_spec = yaml.safe_load(f)

    minimal_spec = {"paths": {}, "components": {"schemas": {}}}
    found = False

    # 1. Find the operation
    for path, methods in full_spec.get("paths", {}).items():
        for method, details in methods.items():
            if details.get("operationId") == target_op_id:
                minimal_spec["paths"][path] = {method: details}
                found = True
                # 2. Basic Schema Extraction (looking for $ref)
                # This is a simple version; it helps Gemini see the 'Body' structure
                import json
                details_str = json.dumps(details)
                for schema_name, schema_body in full_spec.get("components", {}).get("schemas", {}).items():
                    if f"#/components/schemas/{schema_name}" in details_str:
                        minimal_spec["components"]["schemas"][schema_name] = schema_body
                break

    if not found:
        print(f"⚠️ Warning: operationId '{target_op_id}' not found in spec. Sending small sample instead.")
        return f"Operation {target_op_id} not found."

    return yaml.dump(minimal_spec)


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

    # NEW: Only extract what we need
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

    REQUIREMENTS: Use httpx, asyncio, and match the spec schemas. 
    Output ONLY raw python code.
    """

    # Retry logic for 429s
    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)

            out_dir = Path("services") / args.service
            out_dir.mkdir(parents=True, exist_ok=True)
            output_file = out_dir / f"{args.operation}.py"

            clean_code = response.text.strip().removeprefix("```python").removesuffix("```").strip()
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