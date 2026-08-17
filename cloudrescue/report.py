import json
from .engine import run_baseline

def render(indent: int = 2) -> str:
    return json.dumps(run_baseline(), indent=indent, sort_keys=True)
