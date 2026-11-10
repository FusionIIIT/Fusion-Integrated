from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.leave.domain.categories import DEFAULT_ANNUAL_DAYS
from modules.leave.models import AuthorityRule, InstituteOffice, OrgUnit, VacationPeriod
from modules.leave.registry import ROLE_GRANTS
from modules.leave.services import administration
from modules.leave.services.administration import set_policy

EMPLOYEE = tuple(ROLE_GRANTS["staff"])
ADMIN = tuple(ROLE_GRANTS["Leave Administrator"])
STAFF, SUB, OTHER, HEAD, DEAN_HEAD, EST, SANCTION, DIRECTOR = 10, 11, 12, 20, 21, 30, 40, 99

PEOPLE = {
    STAFF: ("staff", "CSE"), SUB: ("staff", "CSE"), OTHER: ("staff", "ECE"),
    HEAD: ("faculty", "CSE"), DEAN_HEAD: ("faculty", "Academics"), EST: ("staff", "Estt"),
    SANCTION: ("staff", "Registry"), DIRECTOR: ("faculty", "Directorate"), 50: ("student", ""),
}
USERS = {uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"Person {uid}",
                      kind=k, department=d) for uid, (k, d) in PEOPLE.items()}


@pytest.fixture
def as_user(stub_iam):
    def _as(uid, perms=EMPLOYEE, modules=("leave_management",)):
        stub_iam(make_session(user_id=uid, kind=PEOPLE[uid][0], permissions=perms,
                              modules=modules), users=USERS)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client
    return _as


@pytest.fixture
def world(db, stub_iam):
    stub_iam(users=USERS)
    for category, days in DEFAULT_ANNUAL_DAYS.items():
        set_policy(category, days, False, None, by=1)
    academics = OrgUnit.objects.create(name="Academics", head_user_id=DEAN_HEAD)
    OrgUnit.objects.create(name="CSE", head_user_id=HEAD, parent=academics)
    for category in ("SCL", "EL", "COL", "VL"):
        AuthorityRule.objects.create(category=category, sanctioning_user_id=SANCTION,
                                     establishment_user_id=EST)
    InstituteOffice.objects.create(code="director", user_id=DIRECTOR)
    cal = administration.create_calendar(2027, "2027", [
        {"date": date(2027, 1, 26), "name": "Republic Day", "kind": "closed"},
        {"date": date(2027, 3, 22), "name": "Holi", "kind": "restricted"}], by=1)
    administration.publish_calendar(cal.pk, by=1)
    VacationPeriod.objects.create(name="Summer", start_date=date(2027, 5, 10),
                                  end_date=date(2027, 7, 20))
