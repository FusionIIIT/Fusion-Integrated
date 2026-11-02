"""Which roles a person may hold, given what they are.

Fusion's authorization has always been a flat list of designation strings. That
list answers "what is this person allowed to do" but never "was this person
allowed to be given that in the first place", and the two are different
questions. `globals_holdsdesignation` is a plain join table: it will happily
record a student as Dean Academic, and in the live data it does.

The model here:

  * A **basic role** — student, faculty or staff — comes from the ERP's
    `user_type`. Exactly one, never assigned, never changed by this console.
  * **Additional roles** are the designations, held on top and held in any
    number. A faculty member is an Associate Professor *and* a HOD *and* the
    Dean Academic at the same time.
  * A role declares which basic roles may hold it. An academic rank belongs to
    faculty; an office belongs to faculty or staff; a functional role — convenor,
    coordinator, warden, committee member — is open to anyone, which is how a
    student becomes a club coordinator.

Uncatalogued roles are allowed and reported rather than refused. The ERP's
academic office adds designations without telling this service, and a role
appearing overnight must not lock its holder out; it must show up on a list
somebody reads.
"""
from __future__ import annotations

from django.conf import settings

from iam.models import IamRole

#: The three basic roles. `compounder` exists in IamUser.KINDS as ERP data but
#: no designation policy references it, so it behaves as staff would.
BASIC_KINDS = ("student", "faculty", "staff")

FACULTY_ONLY = ("faculty",)
FACULTY_OR_STAFF = ("faculty", "staff")
ANYONE = BASIC_KINDS


def may_hold(kind: str, role_code: str, catalogue: dict[str, IamRole]) -> bool:
    """True if a person of this basic role may hold this designation."""
    role = catalogue.get(role_code)
    if role is None or not role.is_active:
        return True
    return role.may_be_held_by(kind)


def exceptions() -> set[tuple[str, str]]:
    """(username, designation) pairs allowed despite the catalogue."""
    raw = getattr(settings, "IAM_ROLE_POLICY_EXCEPTIONS", "") or ""
    out = set()
    for item in raw.split(","):
        username, _, designation = item.strip().partition(":")
        if username and designation:
            out.add((username, designation))
    return out


def load_catalogue() -> dict[str, IamRole]:
    return {r.code: r for r in IamRole.objects.all()}


def violations(pairs, kinds: dict[int, str], usernames: dict[int, str]):
    """Every (user, designation) the catalogue says should not exist.

    `pairs` is the projection's own (erp_user_id, designation) list, so this
    judges exactly what is about to be written rather than a separate query that
    could disagree with it.
    """
    catalogue = load_catalogue()
    found = []
    for erp_user_id, designation in sorted(set(pairs)):
        kind = kinds.get(erp_user_id, "staff")
        if not may_hold(kind, designation, catalogue):
            found.append({
                "erp_user_id": erp_user_id,
                "username": usernames.get(erp_user_id, ""),
                "kind": kind,
                "designation": designation,
            })
    return found


# --- The declared catalogue -------------------------------------------------
#
# Seeded by `manage.py seed_iam_roles`. Only the designations that are actually
# held are listed: cataloguing all 113 rows of globals_designation would be a
# policy claim about roles nobody has, and a wrong claim is worse than none.

CATALOGUE: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    # code, label, category, allowed kinds
    ("student", "Student", IamRole.BASIC, ("student",)),
    # Derived from the curriculum a student's batch belongs to, never assigned.
    # A UG student is not a research scholar; without these, a permission meant
    # for one reaches all 3,027.
    ("ug_student", "Undergraduate", IamRole.BASIC, ("student",)),
    ("pg_student", "Postgraduate", IamRole.BASIC, ("student",)),
    ("phd_student", "Research scholar", IamRole.BASIC, ("student",)),

    ("Professor", "Professor", IamRole.RANK, FACULTY_ONLY),
    ("Associate Professor", "Associate Professor", IamRole.RANK, FACULTY_ONLY),
    ("Assistant Professor", "Assistant Professor", IamRole.RANK, FACULTY_ONLY),

    ("Director", "Director", IamRole.OFFICE, FACULTY_ONLY),
    ("Dean Academic", "Dean (Academic)", IamRole.OFFICE, FACULTY_ONLY),
    ("Dean (R&D)", "Dean (R&D)", IamRole.OFFICE, FACULTY_ONLY),
    ("Dean (P&D)", "Dean (P&D)", IamRole.OFFICE, FACULTY_ONLY),
    ("Dean_s", "Dean (Students)", IamRole.OFFICE, FACULTY_ONLY),
    ("HOD (CSE)", "Head, CSE", IamRole.OFFICE, FACULTY_ONLY),
    ("HOD (ECE)", "Head, ECE", IamRole.OFFICE, FACULTY_ONLY),
    ("HOD (ME)", "Head, Mechanical", IamRole.OFFICE, FACULTY_ONLY),
    ("HOD (Design)", "Head, Design", IamRole.OFFICE, FACULTY_ONLY),
    ("HOD (NS)", "Head, Natural Sciences", IamRole.OFFICE, FACULTY_ONLY),
    ("HOD (Liberal Arts)", "Head, Liberal Arts", IamRole.OFFICE, FACULTY_ONLY),

    ("Registrar", "Registrar", IamRole.OFFICE, FACULTY_OR_STAFF),
    ("Deputy Registrar", "Deputy Registrar", IamRole.OFFICE, FACULTY_OR_STAFF),
    ("acadadmin", "Academic Administrator", IamRole.OFFICE, FACULTY_OR_STAFF),
    ("dracad", "Deputy Registrar (Academic)", IamRole.OFFICE, FACULTY_OR_STAFF),
    ("studentacadadmin", "Student Academic Administrator", IamRole.OFFICE,
     FACULTY_OR_STAFF),
    ("placement_chairman", "Placement Chairman", IamRole.OFFICE, FACULTY_OR_STAFF),
    ("placement_officer", "Placement Officer", IamRole.OFFICE, FACULTY_OR_STAFF),
    ("Junior Assistant", "Junior Assistant", IamRole.OFFICE, ("staff",)),
    ("Senior Assistant", "Senior Assistant", IamRole.OFFICE, ("staff",)),
    ("Upper Division Clerk", "Upper Division Clerk", IamRole.OFFICE, ("staff",)),

    # Open to students on purpose — this is the club-coordinator case.
    ("placement_coordinator", "Placement Coordinator", IamRole.FUNCTIONAL, ANYONE),
    ("Convenor", "Convenor", IamRole.FUNCTIONAL, ANYONE),
    ("Convener", "Convener", IamRole.FUNCTIONAL, ANYONE),
    ("co-ordinator", "Co-ordinator", IamRole.FUNCTIONAL, ANYONE),
    ("co", "Co-ordinator", IamRole.FUNCTIONAL, ANYONE),
    ("mess_committee", "Mess Committee", IamRole.FUNCTIONAL, ANYONE),
    ("mess_convener", "Mess Convener", IamRole.FUNCTIONAL, ANYONE),
    ("Counsellor", "Counsellor", IamRole.FUNCTIONAL, ANYONE),
)
