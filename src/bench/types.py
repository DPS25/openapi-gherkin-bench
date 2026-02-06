from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class SUTContext:
    system_id: str
    base_url: str
    auth_token: Optional[str]
    security_scheme: Optional[str]
    openapi_path: str
    openapi: Dict[str, Any]
    sut_meta: Dict[str, Any]   # from openapi['x-bdd']['sut'] (if present)
    env: Dict[str, Any]        # snapshot of relevant env vars

@dataclass
class Phase:
    name: str          # "warmup" | "run"
    iterations: int
    concurrency: int

@dataclass
class OperationRef:
    role: str          # "write" | "query" | "health"
    id: Optional[str]  # may be "auto"/None; UA resolves via OpenAPI x-bdd.operation

@dataclass
class UniversalJob:
    run_id: str
    plan: Dict[str, Any]          # effective universal plan
    sut: SUTContext               # factory output
    phases: List[Phase]           # warmup/run
    operation_order: List[str]    # e.g. ["write", "query"] for workflow A
