"""Derive HR-EIS wire types from the committed OpenAPI contract and detect drift."""

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "client/src/modules/hreis/api/types.ts"
ALIASES = {
    "ServiceRecord": "RecordRead",
    "CreateRecord": "RecordCreate",
    "HRRequest": "RequestRead",
    "HRRequestDetail": "RequestDetailRead",
    "HRPolicy": "PolicyRead",
    "HRPolicyInput": "PolicyCreate",
    "LeaveInput": "LeaveSubmit",
    "ClaimInput": "ClaimSubmit",
    "AppraisalInput": "AppraisalSubmit",
    "VerifiedLeaveCreditInput": "VerifiedLeaveCredit",
    "VerifiedLeaveCreditRecord": "VerifiedLeaveCreditRead",
    "FinancialReviewRecord": "FinancialReviewRead",
    "HRAudit": "AuditRead",
    "HRNotification": "NotificationRead",
    "HRComplianceRequestStatus": "ComplianceRequest",
    "LeaveBalances": "MyLeaveBalances",
}
ACTIONS = {
    "ClaimReviewInput": "ClaimReview",
    "FinancialReviewInput": "FinancialReview",
    "FinancialProcessingInput": "FinancialProcessing",
    "RequestDecisionInput": "Decision",
    "AssignReviewersInput": "ReviewerAssignment",
    "AppraisalDecisionInput": "AppraisalDecision",
}


def field_name(name):
    return name if re.fullmatch(r"[A-Za-z_$][\w$]*", name) else json.dumps(name)


def ts_type(schema):
    if "$ref" in schema:
        result = schema["$ref"].rsplit("/", 1)[-1]
    elif "enum" in schema:
        result = " | ".join(json.dumps(value) for value in schema["enum"])
    elif "oneOf" in schema or "anyOf" in schema:
        result = " | ".join(ts_type(item) for item in schema.get("oneOf", schema.get("anyOf")))
    elif "allOf" in schema:
        result = " & ".join(ts_type(item) for item in schema["allOf"])
    elif schema.get("type") == "array":
        result = f"Array<{ts_type(schema.get('items', {}))}>"
    elif schema.get("type") == "object" or "properties" in schema:
        properties = schema.get("properties")
        if properties:
            required = set(schema.get("required", []))
            result = (
                "{ "
                + " ".join(
                    f"{field_name(name)}{'' if name in required else '?'}: {ts_type(value)};"
                    for name, value in properties.items()
                )
                + " }"
            )
        else:
            additional = schema.get("additionalProperties", {})
            value_type = ts_type(additional) if isinstance(additional, dict) else "unknown"
            result = f"Record<string, {value_type}>"
    else:
        result = {
            "integer": "number",
            "number": "number",
            "string": "string",
            "boolean": "boolean",
            "null": "null",
        }.get(schema.get("type"), "unknown")
    return f"({result}) | null" if schema.get("nullable") else result


def references(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"].rsplit("/", 1)[-1]
        for nested in value.values():
            yield from references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from references(nested)


def build():
    schemas = yaml.safe_load((ROOT / "openapi/fusion-integrated.v1.yaml").read_text())[
        "components"
    ]["schemas"]
    needed = set(ALIASES.values()) | set(ACTIONS.values())
    pending = list(needed)
    while pending:
        for name in references(schemas[pending.pop()]):
            if name not in needed:
                needed.add(name)
                pending.append(name)
    lines = [
        ("/** Wire types derived from OpenAPI; run python "
         "docs/09-hreis/scripts/hreis_client_types.py. */"),
        "",
    ]
    for name in sorted(needed):
        schema = schemas[name]
        if schema.get("type") == "object" and schema.get("properties"):
            lines.append(f"export interface {name} {{")
            required = set(schema.get("required", []))
            lines.extend(
                f"  {field_name(key)}{'' if key in required else '?'}: {ts_type(value)};"
                for key, value in schema["properties"].items()
            )
            lines.append("}")
        else:
            lines.append(f"export type {name} = {ts_type(schema)};")
        lines.append("")
    pagination = schemas["PaginatedRequestReadList"]
    lines.append("export interface Page<T> {")
    for name, schema in pagination["properties"].items():
        value_type = "T[]" if name == "results" else ts_type(schema)
        optional = "" if name in pagination.get("required", []) else "?"
        lines.append(f"  {name}{optional}: {value_type};")
    lines.extend(["}", ""])
    lines.extend(f"export type {name} = {target};" for name, target in ALIASES.items())
    lines.extend(
        f"export type {name} = {target} & {{ id: number }};" for name, target in ACTIONS.items()
    )
    lines.extend(
        [
            "",
            "export interface RecordFields {",
            "  appointment_details: Record<string, unknown>;",
            "  department: string;",
            "  designation_snapshot: string;",
            "  service_history: unknown[];",
            "  retirement_status: string;",
            "}",
            "",
            "export interface UpdateRecord {",
            "  id: number;",
            "  expected_revision: number;",
            "  fields: Partial<RecordFields>;",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    result = build()
    if options.check:
        if OUTPUT.read_text() != result:
            raise SystemExit(
                "HR-EIS wire types are stale; run python "
                "docs/09-hreis/scripts/hreis_client_types.py"
            )
    else:
        OUTPUT.write_text(result)
        print("HR-EIS wire types refreshed from OpenAPI.")
