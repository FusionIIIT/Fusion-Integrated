from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def enum_values(field, schemas):
    if "enum" in field:
        return set(field["enum"])
    if "$ref" in field:
        return enum_values(schemas[field["$ref"].split("/")[-1]], schemas)
    return set().union(*(enum_values(item, schemas) for item in field.get("allOf", [])))


@pytest.mark.parametrize(
    "resource,field,expected",
    [
        ("Material", "kind", {"FILE", "NOTE", "LINK"}),
        ("Material", "state", {"DRAFT", "SCHEDULED", "PUBLISHED"}),
        ("Assignment", "submission_type", {"FILE", "TEXT", "LINK"}),
        ("Assignment", "state", {"DRAFT", "SCHEDULED", "AVAILABLE"}),
        ("Submission", "kind", {"FILE", "TEXT", "LINK"}),
        ("Grade", "state", {"DRAFT", "RELEASED"}),
    ],
)
def test_committed_response_enums_match_the_client_contract(resource, field, expected):
    schemas = yaml.safe_load((ROOT / "openapi/fusion-integrated.v1.yaml").read_text())[
        "components"
    ]["schemas"]
    contract = schemas[resource]["properties"][field]
    assert contract["readOnly"]
    assert enum_values(contract, schemas) == expected
