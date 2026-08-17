import json

from .engine import run_baseline
from .evaluation import evaluation_summary


def build_report() -> dict:
    report = run_baseline()
    report["model_monitoring_and_robustness"] = evaluation_summary()
    return report


def render(indent: int = 2) -> str:
    return json.dumps(build_report(), indent=indent, sort_keys=True)
