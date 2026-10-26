import runpy
import sys

path = sys.argv[1]
ns = runpy.run_path(path)
text = open(path, encoding="utf-8-sig").read()

exp_codes = {
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.view",
    "leave.request.delete",
    "leave.request.review",
    "leave.request.assign",
    "leave.request.approve",
    "leave.resumption.create",
    "leave.resumption.review",
    "leave.substitute.review",
    "leave.policy.manage",
    "leave.calendar.publish",
    "leave.record.manage",
}

errs = []

if ns["MODULE"]["code"] != "leave":
    errs.append("MODULE code is not 'leave'")

codes = [c for c, _ in ns["PERMISSIONS"]]

if len(codes) != len(set(codes)):
    errs.append("duplicate permission codes")

if set(codes) != exp_codes:
    errs.append(
        f"permission set differs: missing={exp_codes-set(codes)} "
        f"extra={set(codes)-exp_codes}"
    )

if "elm." in text:
    errs.append("an 'elm.' string remains")

roles = ns["ROLE_GRANTS"]

exp_roles = {
    "faculty", "staff", "unit_head", "hod", "deputy_registrar",
    "dean", "registrar", "director", "leave_administrator"
}

if set(roles) != exp_roles:
    errs.append(f"role names differ: {set(roles) ^ exp_roles}")

fac = {
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.delete",
    "leave.resumption.create",
    "leave.substitute.review",
}

want = {
    "faculty": fac,
    "staff": fac,
    "unit_head": fac | {
        "leave.request.review", "leave.request.view"
    },
    "hod": fac | {
        "leave.request.review", "leave.request.view"
    },
    "deputy_registrar": fac | {
        "leave.request.assign", "leave.request.view"
    },
    "dean": fac | {
        "leave.request.approve", "leave.resumption.review",
        "leave.request.view"
    },
    "registrar": fac | {
        "leave.request.approve", "leave.resumption.review",
        "leave.request.view"
    },
    "director": fac | {
        "leave.request.approve", "leave.resumption.review",
        "leave.request.view", "leave.request.review"
    },
    "leave_administrator": {
        "leave.request.view_self",
        "leave.request.view",
        "leave.policy.manage",
        "leave.calendar.publish",
        "leave.record.manage",
    },
}

for role, expected in want.items():
    actual_list = roles.get(role, [])
    actual = set(actual_list)

    if len(actual_list) != len(actual):
        errs.append(f"{role}: duplicate codes")

    if actual != expected:
        errs.append(
            f"{role}: missing={expected-actual} extra={actual-expected}"
        )

held = set().union(*[set(v) for v in roles.values()])

if set(codes) - held:
    errs.append(f"permissions nobody holds: {set(codes)-held}")

for item in ns["NAV_ITEMS"]:
    if item["required_permission"] not in codes:
        errs.append(f"nav {item['code']} uses unknown permission")

print("PASS: all checks passed" if not errs else "FAIL:\n- " + "\n- ".join(errs))
