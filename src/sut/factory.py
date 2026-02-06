import os
import yaml
from pathlib import Path
from src.bench.types import SUTContext

SYSTEMS_ROOT = Path("specs/systems")

class SUTFactory:
    def build_from_feature(self, feature_bundle: dict) -> dict:

        return self.build(plan={})
    
    def build(self, plan: dict) -> dict:
        # 1) read env selection
        sut_id = os.getenv("SUT_ID")  # e.g. "influxdb/v2" 
        if not sut_id:
            raise ValueError("SUT_ID env missing")

        base_url = os.getenv("SUT_BASE_URL", "").strip()
        auth_token = os.getenv("SUT_AUTH_TOKEN")
        security_scheme = os.getenv("SUT_SECURITY_SCHEME")

        # 2) resolve openapi.yaml path from SUT_ID
        # SUT_ID = "influxdb/v2"
        # => specs/systems/influxdb/v2/openapi.yaml
        openapi_path = SYSTEMS_ROOT / sut_id / "openapi.yaml"
        if not openapi_path.exists():
            # optionally: support "influxdb@v2" or "influxdb/v2" variants
            raise FileNotFoundError(f"OpenAPI not found for SUT_ID={sut_id}: {openapi_path}")

        openapi = yaml.safe_load(openapi_path.read_text(encoding="utf-8")) or {}

        # 3) extract x-bdd.sut meta if present
        sut_meta = (openapi.get("x-bdd") or {}).get("sut") or {}

        # 4) build SUTContext
        env_snapshot = {
            "SUT_ID": sut_id,
            "SUT_BASE_URL": base_url,
            "SUT_AUTH_TOKEN": "***" if auth_token else None,
            "SUT_SECURITY_SCHEME": security_scheme,
        }

        ctx = SUTContext(
            system_id=sut_id,
            base_url=base_url,
            auth_token=auth_token,
            security_scheme=security_scheme,
            openapi_path=str(openapi_path),
            openapi=openapi,
            sut_meta=sut_meta,
            env=env_snapshot,
        )

        return {
            "system_id": sut_id,
            "openapi_path": str(openapi_path),
            "openapi": openapi,
            "sut_meta": sut_meta,
            "env": env_snapshot,
            "sut": ctx,  # convenience: pass typed object
        }
