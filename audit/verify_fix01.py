import runpy
from pathlib import Path

original = runpy.run_path("modules/leave/registry.py")
candidate_path = Path("audit/prompts/registry_candidate.py")
ns = runpy.run_path(str(candidate_path))
expected = [
    ("leave.request.create", "Apply for leave or request extension of ongoing leave"),
    ("leave.request.view_self", "View own leave history, balances, and export own applications"),
    ("leave.request.view", "View leave requests in your approval queue"),
    ("leave.request.delete", "Withdraw a pending request or request cancellation of approved leave"),
    ("leave.request.review", "Unit Head review, decision or recommendation"),
    ("leave.request.assign", "Establishment verification and routing to the sanctioning authority"),
    ("leave.request.approve", "Make final sanctioning decisions"),
    ("leave.resumption.create", "Submit duty resumption after EL, COL or VL"),
    ("leave.resumption.review", "Review duty resumption declarations"),
    ("leave.substitute.review", "Accept or decline a nominated substitute responsibility"),
    ("leave.policy.manage", "Configure leave policy, hierarchy and SLA thresholds"),
    ("leave.calendar.publish", "Maintain and publish the holiday and RH calendar"),
    ("leave.record.manage", "Record already-sanctioned offline leave and maintain leave records"),
]
assert ns["PERMISSIONS"] == expected, "permission tuples/order/labels differ"
assert ns["MODULE"]["code"] == "leave"
assert {k: v for k, v in ns["MODULE"].items() if k != "code"} == {
    k: v for k, v in original["MODULE"].items() if k != "code"
}, "other MODULE values changed"
nav_fields = ("code", "label", "icon", "to", "sort_order")
assert [[x[k] for k in nav_fields] for x in ns["NAV_ITEMS"]] == [
    [x[k] for k in nav_fields] for x in original["NAV_ITEMS"]
], "NAV_ITEMS metadata or order changed"
assert "elm." not in candidate_path.read_text(encoding="utf-8-sig")
long = [(i, len(line)) for i, line in enumerate(
    candidate_path.read_text(encoding="utf-8-sig").splitlines(), 1
) if len(line) >= 100]
assert not long, f"lines >=100 chars: {long}"
print("PASS: permissions exact/in-order; module and navigation preserved; no elm.; all lines <100")
