from pathlib import Path

from src.sut.factory import SUTFactory
from src.sut.gemini_contract.client import GeminiClient
from src.sut.universal_adapter_skeleton import UniversalAdapter
from src.bench.data_gen import DataGenerator
from src.bench.plan_runner import PlanRunner
from src.export.result_sink import ResultSink


def before_scenario(context, scenario):
    context.gherkin_steps = []
    context.gherkin_docstrings = []
    context.run_result = None


def after_scenario(context, scenario):
    """
    Single execution point:
    - No dependence on any concrete step text.
    - We always run once after the scenario, using the raw feature context.
    """
    feature_path = getattr(context.feature, "filename", None)
    if not feature_path:
        raise RuntimeError("Could not determine feature file path from context.feature.filename")

    factory = SUTFactory()
    gemini = GeminiClient()
    ua = UniversalAdapter(gemini=gemini)
    data_gen = DataGenerator()
    sink = ResultSink()

    runner = PlanRunner(
        factory=factory,
        universal_adapter=ua,
        data_gen=data_gen,
        result_sink=sink,
    )


    context.run_result = runner.run_from_feature(
        feature_path=feature_path,
        scenario_name=scenario.name,
        gherkin_steps=context.gherkin_steps,
        gherkin_docstrings=context.gherkin_docstrings,
    )
