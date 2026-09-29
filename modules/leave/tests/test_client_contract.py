"""The exact shapes the client sends, checked against the serializers."""
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.api import serializers as s
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db
U = 701


@pytest.fixture
def ready():
    UserRef.objects.create(user_id=U, username=f"u{U}", display_name="U",
                           kind="faculty", department="CSE")
    factories.setup_all(U)


def client(stub_iam):
    stub_iam(make_session(user_id=U, kind="faculty", modules=("leave",),
                          permissions=("leave.request.create",
                                       "leave.request.view_self")))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


#: Verbatim from client/src/modules/leave/pages/ApplyPage.tsx.
def client_payload(**over):
    body = {
        "category": "CL",
        "starts_on": str(date(YEAR, 3, 2)),
        "ends_on": str(date(YEAR, 3, 3)),
        "reason": "Family commitment",
        "half": None,
        "substitute_user_id": None,
        "station": None,
    }
    return {**body, **over}


class TestTheApplicationPayload:
    def test_the_plain_shape_is_accepted(self, stub_iam, ready):
        c = client(stub_iam)

        assert c.post("/api/v1/leave/requests", client_payload(),
                      format="json").status_code == 201

    def test_station_leave_is_accepted(self, stub_iam, ready):
        c = client(stub_iam)

        response = c.post("/api/v1/leave/requests", client_payload(station={
            "destination": "Bhopal",
            "from_date": str(date(YEAR, 3, 2)),
            "to_date": str(date(YEAR, 3, 3)),
        }), format="json")

        assert response.status_code == 201, response.json()

    def test_the_station_details_are_kept(self, stub_iam, ready):
        c = client(stub_iam)

        created = c.post("/api/v1/leave/requests", client_payload(station={
            "destination": "Bhopal",
            "from_date": str(date(YEAR, 3, 2)),
            "to_date": str(date(YEAR, 3, 3)),
        }), format="json").json()

        assert created["station_leave"] is True
        assert created["station_destination"] == "Bhopal"

    def test_a_half_day_is_accepted_on_a_single_date(self, stub_iam, ready):
        c = client(stub_iam)

        response = c.post("/api/v1/leave/requests", client_payload(
            ends_on=str(date(YEAR, 3, 2)), half="FIRST"), format="json")

        assert response.status_code == 201

    def test_a_half_day_over_several_days_is_a_400_not_a_500(self, stub_iam, ready):
        c = client(stub_iam)

        # Reachable from the form: pick a half day, then widen the dates.
        response = c.post("/api/v1/leave/requests", client_payload(half="FIRST"),
                          format="json")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "half_day_over_several_days"


class TestTheSerializerKeysMatchTheClient:
    def test_station_uses_the_keys_the_client_sends(self):
        declared = set(s.StationSerializer().get_fields())

        assert declared == {"destination", "from_date", "to_date"}

    def test_a_transition_carries_an_id_for_the_client_to_key_on(self):
        assert "id" in s.LeaveTransitionSerializer().get_fields()

    def test_the_policy_shape_includes_every_field_the_policy_has(self):
        from modules.leave.models import LeavePolicy

        exposed = set(s.PolicySerializer().get_fields())
        stored = {f.name for f in LeavePolicy._meta.get_fields()
                  if getattr(f, "concrete", False)}
        missing = stored - exposed - {"created_at", "updated_at", "rules"}

        assert missing == set(), f"policy fields the API never shows: {missing}"
