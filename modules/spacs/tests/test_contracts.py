"""Tests for SPACS public contracts."""
import pytest

from modules.spacs import contracts
from modules.spacs.models import (
    AwardCandidate,
    AwardCycle,
    ScholarshipApplication,
    SchemeCatalogue,
    SchemePolicyVersion,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def awards_data():
    scheme = SchemeCatalogue.objects.create(code="mcm", name="MCM Scholarship", scheme_type="scholarship", status="published")
    ver = SchemePolicyVersion.objects.create(scheme=scheme, version_number=1, title="MCM v1", status="published")

    app1 = ScholarshipApplication.objects.create(
        application_number="SPACS-1001",
        student_user_id=1001,
        scheme=scheme,
        policy_version=ver,
        academic_cycle="2026-27",
        status="approved",
    )

    award_scheme = SchemeCatalogue.objects.create(code="gold-medal", name="Director Gold", scheme_type="award", status="published")
    award_ver = SchemePolicyVersion.objects.create(scheme=award_scheme, version_number=1, title="Gold v1", status="published")
    cycle = AwardCycle.objects.create(
        scheme=award_scheme,
        policy_version=award_ver,
        academic_cycle="2025-26",
        convocation_year=2026,
        status="published",
    )
    cand = AwardCandidate.objects.create(
        award_cycle=cycle,
        student_user_id=1001,
        source_method="academic_pool",
        final_outcome="approved",
    )
    return {"scheme": scheme, "app": app1, "cand": cand}


def test_get_scholarship_awards_empty():
    assert contracts.get_scholarship_awards([]) == {}


def test_get_scholarship_awards(awards_data):
    res = contracts.get_scholarship_awards([1001, 2002])
    assert 1001 in res
    assert 2002 in res
    assert len(res[1001]) == 1
    assert res[1001][0].scheme_code == "mcm"
    assert len(res[2002]) == 0


def test_get_convocation_awards(awards_data):
    res = contracts.get_convocation_awards([1001, 2002], convocation_year=2026)
    assert 1001 in res
    assert len(res[1001]) == 1
    assert res[1001][0].scheme_code == "gold-medal"


def test_get_spacs_clearances():
    res = contracts.get_spacs_clearances([1001, 2002])
    assert res[1001].cleared is True
    assert res[2002].cleared is True
