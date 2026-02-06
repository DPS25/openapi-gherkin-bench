# Later: schema -> payload (example -> default -> enum -> null) like in Mermaid.

class DataGenerator:
    def prepare(self, bench_spec: dict, openapi: dict, sut) -> object:
        def provider(role=None, step=None, i=0):
            return {}
        return provider
    
    def generate(self, openapi: dict, op_mapping: dict, role: str, universal_plan: dict) -> dict:
        # 1) find schema for requestBody for the resolved operation
        # 2) prefer examples.default.value
        # 3) else build object by walking schema (required fields)
        # 4) fill primitives:
        #    - example > default > enum[0] > null
        return {}
