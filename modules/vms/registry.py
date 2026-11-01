"""Permissions this module recognises. No nav yet: it has no screens of its own."""

PERMISSIONS = [
    ("vms.request.create", "Raise a visit request"),
    ("vms.request.decide", "Approve or reject a visit request"),
    ("vms.gate.operate", "Check visitors in and out at the gate"),
    ("vms.blacklist.manage", "Maintain the visitor blacklist"),
    ("vms.policy.publish", "Publish an access policy version"),
]

SYSTEM_PERMISSIONS = []

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": ["vms.request.create"],
    "Dean Academic": ["vms.request.create", "vms.request.decide",
                      "vms.policy.publish"],
    "acadadmin": ["vms.request.create", "vms.request.decide",
                  "vms.gate.operate", "vms.blacklist.manage",
                  "vms.policy.publish"],
}
