"""Who sees which rows, over HTTP (IAA-BR-004, 501). Out-of-scope rows are 404, not 403."""
import pytest

from modules.iaa.domain import roles
from modules.iaa.services import anomalies, observations, review
from modules.iaa.tests.helpers import FACULTY, actor, api_client, new_expense, new_ta

pytestmark = pytest.mark.django_db

B = "/api/v1/iaa"


def _ids(response):
    assert response.status_code == 200, response.content
    return {row["id"] for row in response.json()["results"]}


@pytest.fixture
def world(people, configured):
    mine = new_expense(people.creator)                                   # CSE, submitted
    theirs = new_expense(people.other)                                   # CSE, submitted
    draft = new_expense(people.creator, submit=False)
    ece = new_expense(people.creator, department="ECE")
    review.validate(people.finance, mine.pk)                             # HoD CSE holds it
    review.validate(people.finance, ece.pk)                              # HoD ECE holds it
    return {"mine": mine, "theirs": theirs, "draft": draft, "ece": ece}


# IAA-BR-501: active role plus ownership or assignment decides what is visible
def test_a_requester_sees_only_their_own_items_including_drafts(stub_iam, world):
    client = api_client(stub_iam, 101, FACULTY)
    assert _ids(client.get(f"{B}/records")) == {world["mine"].pk, world["draft"].pk,
                                                world["ece"].pk}
    other = api_client(stub_iam, 102, FACULTY)
    assert _ids(other.get(f"{B}/records")) == {world["theirs"].pk}


def test_someone_elses_item_is_a_404_in_detail_history_and_every_action(stub_iam, world):
    client = api_client(stub_iam, 102, FACULTY)
    pk = world["mine"].pk
    assert client.get(f"{B}/records/{pk}").status_code == 404
    assert client.get(f"{B}/records/{pk}/history").status_code == 404
    assert client.patch(f"{B}/records/{pk}", {"title": "x"}, format="json").status_code == 404
    assert client.post(f"{B}/records/{pk}/submit").status_code == 404
    assert client.post(f"{B}/records/{pk}/documents",
                       {"title": "t", "link": "https://x.test/a"},
                       format="json").status_code == 404


def test_finance_and_the_auditor_see_everything_submitted_but_never_drafts(stub_iam, world):
    expected = {world["mine"].pk, world["theirs"].pk, world["ece"].pk}
    for uid, role in ((201, roles.FINANCE), (401, roles.AUDITOR)):
        client = api_client(stub_iam, uid, role)
        assert _ids(client.get(f"{B}/records")) == expected
        assert client.get(f"{B}/records/{world['draft'].pk}").status_code == 404


def test_the_system_admin_sees_no_operational_data_at_all(stub_iam, world):
    client = api_client(stub_iam, 501, roles.SYSTEM_ADMIN)
    assert client.get(f"{B}/records").status_code == 403            # no code to even list
    assert client.get(f"{B}/records/{world['mine'].pk}").status_code == 403
    assert client.get(f"{B}/notifications").status_code == 403
    assert client.get(f"{B}/config/policies").status_code == 200    # configuration only


def test_an_hod_sees_only_items_assigned_to_their_department(stub_iam, world):
    cse = api_client(stub_iam, 301, roles.HOD)
    assert _ids(cse.get(f"{B}/records")) == {world["mine"].pk}
    assert cse.get(f"{B}/records/{world['ece'].pk}").status_code == 404
    ece = api_client(stub_iam, 304, roles.HOD)
    assert _ids(ece.get(f"{B}/records")) == {world["ece"].pk}
    assert ece.get(f"{B}/records/{world['mine'].pk}").status_code == 404


def test_the_dean_sees_nothing_until_an_item_reaches_the_dean(stub_iam, people, world):
    dean = api_client(stub_iam, 302, roles.DEAN)
    assert _ids(dean.get(f"{B}/records")) == set()
    big = new_expense(people.creator, amount="60000")
    review.validate(people.finance, big.pk)
    from modules.iaa.services import decisions
    decisions.decide(people.hod, big.pk, decision="approve", remarks="up")
    dean = api_client(stub_iam, 302, roles.DEAN)
    assert _ids(dean.get(f"{B}/records")) == {big.pk}


def test_an_hod_with_no_known_department_sees_nothing(stub_iam, world):
    client = api_client(stub_iam, 777, roles.HOD)                    # not in the directory
    assert _ids(client.get(f"{B}/records")) == set()


def test_queue_filters_stay_inside_scope(stub_iam, world):
    finance = api_client(stub_iam, 201, roles.FINANCE)
    assert _ids(finance.get(f"{B}/records?queue=finance_review")) == {world["theirs"].pk}
    hod = api_client(stub_iam, 301, roles.HOD)
    assert _ids(hod.get(f"{B}/records?queue=pending_approval")) == {world["mine"].pk}


def test_hostile_filter_values_are_a_400_not_a_500(stub_iam, world):
    client = api_client(stub_iam, 201, roles.FINANCE)
    for query in ("kind=bogus", "status=bogus", "queue=bogus", "kind='; DROP TABLE x;--"):
        assert client.get(f"{B}/records?{query}").status_code == 400, query
    assert client.get(f"{B}/reports/summary?financial_year_id=abc").status_code == 400
    assert api_client(stub_iam, 401, roles.AUDITOR).get(
        f"{B}/anomalies?status=bogus").status_code == 400
    assert api_client(stub_iam, 401, roles.AUDITOR).get(
        f"{B}/observations?status=bogus").status_code == 400


def test_anomalies_are_visible_only_to_the_roles_they_concern(stub_iam, people, world):
    # ECE has no allocation, so validating its claim already raised an automatic budget anomaly
    automatic = _ids(api_client(stub_iam, 201, roles.FINANCE).get(f"{B}/anomalies"))
    assert len(automatic) == 1
    finance_flag = anomalies.flag(people.finance, category="budget", description="x")
    anomalies.escalate(people.finance, finance_flag.pk, remarks="up")        # now the Dean's
    own = anomalies.flag(people.finance, category="policy", description="y")
    assert _ids(api_client(stub_iam, 201, roles.FINANCE).get(f"{B}/anomalies")) == (
        automatic | {finance_flag.pk, own.pk})
    assert _ids(api_client(stub_iam, 302, roles.DEAN).get(f"{B}/anomalies")) == {
        finance_flag.pk}
    assert _ids(api_client(stub_iam, 303, roles.DIRECTOR).get(f"{B}/anomalies")) == set()
    assert api_client(stub_iam, 101, FACULTY).get(f"{B}/anomalies").status_code == 403


def test_observations_are_visible_to_auditors_finance_and_their_respondent_only(
        stub_iam, people, world):
    obs = observations.raise_observation(people.auditor, title="t", detail="d",
                                         record_id=world["mine"].pk)
    assert _ids(api_client(stub_iam, 101, FACULTY).get(f"{B}/observations")) == {obs.pk}
    assert _ids(api_client(stub_iam, 102, FACULTY).get(f"{B}/observations")) == set()
    assert _ids(api_client(stub_iam, 401, roles.AUDITOR).get(f"{B}/observations")) == {obs.pk}
    assert api_client(stub_iam, 301, roles.HOD).get(f"{B}/observations").status_code == 403
    other = api_client(stub_iam, 102, FACULTY)
    assert other.post(f"{B}/observations/{obs.pk}/respond",
                      {"corrective_action": "x"}, format="json").status_code == 404


def test_notifications_reach_only_the_right_people(stub_iam, people, world):
    mine = api_client(stub_iam, 101, FACULTY).get(f"{B}/notifications").json()
    assert mine["notifications"] and all("message" in n for n in mine["notifications"])
    theirs = api_client(stub_iam, 102, FACULTY).get(f"{B}/notifications").json()
    assert {n["entity_id"] for n in theirs["notifications"]} == {world["theirs"].pk}
    hod = api_client(stub_iam, 301, roles.HOD).get(f"{B}/notifications").json()
    assert hod["pending"]["to_decide"] == 1
    finance = api_client(stub_iam, 201, roles.FINANCE).get(f"{B}/notifications").json()
    assert finance["pending"]["to_review"] == 1
    auditor = api_client(stub_iam, 401, roles.AUDITOR).get(f"{B}/notifications").json()
    assert auditor["pending"]["to_verify"] == 0


def test_a_ta_claim_is_scoped_the_same_way(stub_iam, people, configured):
    claim = new_ta(people.creator)
    assert _ids(api_client(stub_iam, 101, FACULTY).get(f"{B}/records?kind=ta")) == {claim.pk}
    assert _ids(api_client(stub_iam, 102, FACULTY).get(f"{B}/records?kind=ta")) == set()
    assert actor(102, FACULTY)                                        # helper is importable
