"""Person A never sees or changes person B's rows, by id, filter, search, export or body id."""
import pytest
from django.utils import timezone

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Document,
    DocumentVersion,
    Inventor,
    LicensingRequest,
    PriorArtReference,
)
from modules.pms.tests.conftest import (
    ATTORNEY,
    ATTORNEY_2,
    CO_INVENTOR,
    DIRECTOR,
    DIRECTOR_2,
    OTHER_APPLICANT,
    approved_with_attorney,
    make_app,
    with_cycle,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def two(world):
    mine = make_app(sm.UNDER_REVIEW, title="Mine")
    with_cycle(mine)
    theirs = make_app(sm.UNDER_REVIEW, applicant=OTHER_APPLICANT, domain="software",
                      title="Theirs")
    return mine, theirs


# BR-PMS-003
def test_another_applicants_application_is_404_not_403_br_pms_003(world, two):
    _, theirs = two
    a = world["applicant"]
    for path in (f"applications/{theirs.pk}", f"applications/{theirs.pk}/history",
                 f"applications/{theirs.pk}/documents", "applications/999999"):
        assert a.get(path).status_code == 404, path
    assert a.get(f"applications/{theirs.pk}/prior-art").json() == []


def test_another_applicants_application_cannot_be_changed(world, two):
    _, theirs = two
    a = world["applicant"]
    assert a.patch(f"applications/{theirs.pk}", {"title": "Mine now"}).status_code == 404
    assert a.post(f"applications/{theirs.pk}/withdraw", {"reason": "x"}).status_code == 404
    assert a.post(f"applications/{theirs.pk}/appeal", {"grounds": "g",
                                                      "justification": "j"}).status_code == 404
    theirs.refresh_from_db()
    assert theirs.title == "Theirs" and theirs.status == sm.UNDER_REVIEW


def test_list_filter_and_search_never_include_others(world, two):
    a = world["applicant"]
    rows = a.get("applications", {"q": "Theirs"}).json()["results"]
    assert rows == []
    rows = a.get("applications", {"domain_code": "software"}).json()["results"]
    assert rows == []
    assert [r["title"] for r in a.get("applications").json()["results"]] == ["Mine"]


# BR-PMS-003
def test_reports_and_exports_never_include_others_br_pms_003(world, two):
    a = world["applicant"]
    titles = [r["title"] for r in a.get("reports/status").json()["rows"]]
    assert titles == ["Mine"]
    assert world["other"].client.get("/api/v1/pms/reports/status/export").status_code == 403


def test_a_body_id_outside_scope_is_404(world, two):
    _, theirs = two
    a = world["applicant"]
    assert a.post("prior-art/searches", {"query": "x", "application_id": theirs.pk}) \
        .status_code == 404
    assert a.post("licensing-requests", {"application_id": theirs.pk, "kind": "licensing",
                                         "summary": "s"}).status_code == 404
    assert not LicensingRequest.objects.exists()


def test_consent_for_another_applications_inventor_is_refused(world, two):
    mine, theirs = two
    stranger = Inventor.objects.filter(application=theirs).first()
    r = world["applicant"].post(f"applications/{mine.pk}/withdraw", {
        "reason": "x", "consented_inventor_ids": [stranger.pk]})
    assert r.json()["error"]["code"] == "unknown_inventor"


# BR-PMS-006
def test_a_director_outside_their_area_and_unassigned_sees_nothing_br_pms_006(world, two):
    _, theirs = two
    assert world["director"].get(f"applications/{theirs.pk}").status_code == 404
    assert world["director"].get("reports/status").json()["rows"][0]["title"] == "Mine"


def test_an_unassigned_attorney_sees_nothing(world):
    app = approved_with_attorney(ATTORNEY)
    assert world["attorney2"].get(f"applications/{app.pk}").status_code == 404
    offer = app.attorney_assignments.get()
    assert world["attorney2"].post(f"attorney-assignments/{offer.pk}/respond",
                                   {"accept": True}).status_code == 404
    assert world["attorney2"].post(f"applications/{app.pk}/filings", {
        "jurisdiction": "IN", "office_name": "IPO", "external_filing_id": "IN123",
        "filing_date": str(timezone.localdate()),
        "confirmation_reference": "c"}).status_code == 404


def test_pcc_admin_never_sees_someone_elses_draft(world):
    d = make_app(sm.DRAFT)
    assert world["pcc"].get(f"applications/{d.pk}").status_code == 404
    assert world["pcc"].get("applications").json()["results"] == []


def test_a_co_inventor_reads_but_cannot_act_ruling_c16(world, two):
    mine, _ = two
    Inventor.objects.create(application=mine, user_id=CO_INVENTOR, name="Co",
                            share_percent=50)
    c = world["co_inventor"]
    assert c.get(f"applications/{mine.pk}").status_code == 200
    assert c.post(f"applications/{mine.pk}/withdraw", {"reason": "x"}).json()["error"][
        "code"] == "not_applicant"
    assert c.get("reports/status").json()["rows"] == []


def _doc(app, sensitivity):
    doc = Document.objects.create(application=app, kind="claims", title=sensitivity,
                                  sensitivity=sensitivity, created_by_user_id=1001)
    DocumentVersion.objects.create(document=doc, number=1, storage_key=f"s{doc.pk}",
                                   original_name="c.pdf", size_bytes=5, sha256="0" * 64,
                                   scanner="clamd", uploaded_by_user_id=1001)
    return doc


# BR-PMS-084 BR-PMS-130 BR-PMS-086 PMS-AFR-058 PMS-AFR-154 PMS-AFR-156
def test_document_sensitivity_limits_readers_br_pms_084_br_pms_130(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, director=DIRECTOR)
    for level in ("confidential", "restricted"):
        _doc(app, level)
    seen = {d["title"] for d in world["director"].get(f"applications/{app.pk}/documents").json()}
    assert seen == {"Spec", "confidential", "restricted"}
    area_only = {d["title"] for d in
                 world["director2"].get(f"applications/{app.pk}/documents").json()}
    assert "confidential" not in area_only and "restricted" not in area_only
    hidden = DocumentVersion.objects.get(document__title="restricted")
    assert world["director2"].get(f"documents/versions/{hidden.pk}/download").status_code == 404


def test_a_past_director_reads_confidential_but_not_restricted_ruling_c16(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, director=DIRECTOR_2, status="reassigned")
    with_cycle(app, director=DIRECTOR)
    for level in ("confidential", "restricted"):
        _doc(app, level)
    titles = {d["title"] for d in
              world["director2"].get(f"applications/{app.pk}/documents").json()}
    assert "confidential" in titles and "restricted" not in titles


def test_prior_art_ranking_never_shows_others_references_blueprint_s_2(world, two):
    _, theirs = two
    PriorArtReference.objects.create(application=theirs, kind="patent", title="graphene",
                                     added_by_user_id=OTHER_APPLICANT)
    body = world["applicant"].post("prior-art/searches", {"query": "graphene"}).json()
    assert body["results"] == []


# BR-PMS-091 PMS-AFR-164
def test_licensing_is_visible_only_to_its_parties_br_pms_091(world, two):
    mine, _ = two
    LicensingRequest.objects.create(application=mine, applicant_user_id=1001,
                                    kind="licensing", summary="s")
    assert world["other"].get("licensing-requests").json() == []
    assert world["director"].get("licensing-requests").json() == []
    assert len(world["pcc"].get("licensing-requests").json()) == 1
    assert len(world["applicant"].get("licensing-requests").json()) == 1


def test_attorney_cannot_see_other_attorneys_assignments(world):
    approved_with_attorney(ATTORNEY_2)
    assert world["attorney"].get("my-work").json() == []
    assert world["attorney"].get("applications").json()["results"] == []
