import json
from pathlib import Path


ROOT = Path(__file__).parents[2]


def design(strategy):
    return json.loads((ROOT / "a8_design" / f"{strategy}_DESIGN.json").read_text(encoding="utf-8"))


def not_automated_ids(strategy):
    return [
        case["source_id"]
        for case in design(strategy)["cases"]
        if case["test_type"] == "NOT_AUTOMATED"
    ]

