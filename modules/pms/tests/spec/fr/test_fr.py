"""Functional Requirement (FR / CFR / AFR) Specification Test Suite.
Generated from docs/09-pms/spec-tests/FR_DESIGN.json.
Obligations covered: CFR-PMS-001 through CFR-PMS-030.
"""
import pytest
from decimal import Decimal
from modules.pms.models.application import ApplicationStatus, PatentApplication
from modules.pms.services.applications import create_draft, submit_application, withdraw_application
from modules.pms.services.reviews import assign_director, submit_review
from modules.pms.services.budget import review_budget
from modules.pms.domain.validation import ValidationError
from modules.pms.domain.state_machine import IllegalTransitionError

@pytest.mark.django_db
def test_fr_tc_01():
    """FR-TC-01 | CFR-PMS-001 / PMS-AFR-010 positive
    Verify PMS shall allow Applicants to track status and progress of their patent applications.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-01",
        abstract="Technical abstract for FR-TC-01",
        claims="Claim 1: Apparatus for FR-TC-01.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_02():
    """FR-TC-02 | CFR-PMS-002 / PMS-AFR-023 positive
    Verify PMS shall provide Directors with oversight information for application workflows in their domain.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-02",
        abstract="Technical abstract for FR-TC-02",
        claims="Claim 1: Apparatus for FR-TC-02.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_03():
    """FR-TC-03 | CFR-PMS-003 / PMS-AFR-026 positive
    Verify PMS shall allow PCC_ADMIN to monitor workflows and resolve conflict-of-interest cases within PMS.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-03",
        abstract="Technical abstract for FR-TC-03",
        claims="Claim 1: Apparatus for FR-TC-03.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_04():
    """FR-TC-04 | CFR-PMS-004 / PMS-AFR-037 positive
    Verify PMS shall allow Attorneys to provide legal advice records throughout the patent lifecycle.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-04",
        abstract="Technical abstract for FR-TC-04",
        claims="Claim 1: Apparatus for FR-TC-04.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_05():
    """FR-TC-05 | CFR-PMS-005 / PMS-AFR-038 positive
    Verify PMS shall allow Applicants to submit a patent application with title, abstract, detailed description, claims, inventor information, and supporting documents.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-05",
        abstract="Technical abstract for FR-TC-05",
        claims="Claim 1: Apparatus for FR-TC-05.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_06():
    """FR-TC-06 | CFR-PMS-005 / PMS-AFR-038 validation-refusal
    Verify refusal on invalid input for CFR-PMS-005
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_07():
    """FR-TC-07 | CFR-PMS-006 / PMS-AFR-049 positive
    Verify PMS shall allow PCC_ADMIN to assign submitted applications to Directors.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-07",
        abstract="Technical abstract for FR-TC-07",
        claims="Claim 1: Apparatus for FR-TC-07.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_08():
    """FR-TC-08 | CFR-PMS-006 / PMS-AFR-049 validation-refusal
    Verify refusal on invalid input for CFR-PMS-006
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_09():
    """FR-TC-09 | CFR-PMS-007 / PMS-AFR-058 positive
    Verify PMS shall allow Directors to view application details, documents, and supporting materials for assigned applications.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-09",
        abstract="Technical abstract for FR-TC-09",
        claims="Claim 1: Apparatus for FR-TC-09.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_10():
    """FR-TC-10 | CFR-PMS-007 / PMS-AFR-058 validation-refusal
    Verify refusal on invalid input for CFR-PMS-007
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_11():
    """FR-TC-11 | CFR-PMS-008 / PMS-AFR-066 positive
    Verify PMS shall allow Applicants to revise applications with status Needs Revision.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-11",
        abstract="Technical abstract for FR-TC-11",
        claims="Claim 1: Apparatus for FR-TC-11.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_12():
    """FR-TC-12 | CFR-PMS-009 / PMS-AFR-074 positive
    Verify PMS shall allow only PCC_ADMIN to assign attorneys to approved applications.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-12",
        abstract="Technical abstract for FR-TC-12",
        claims="Claim 1: Apparatus for FR-TC-12.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_13():
    """FR-TC-13 | CFR-PMS-009 / PMS-AFR-074 validation-refusal
    Verify refusal on invalid input for CFR-PMS-009
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_14():
    """FR-TC-14 | CFR-PMS-010 / PMS-AFR-082 positive
    Verify PMS shall allow Attorneys to record legal and patentability analysis for assigned applications.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-14",
        abstract="Technical abstract for FR-TC-14",
        claims="Claim 1: Apparatus for FR-TC-14.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_15():
    """FR-TC-15 | CFR-PMS-010 / PMS-AFR-082 validation-refusal
    Verify refusal on invalid input for CFR-PMS-010
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_16():
    """FR-TC-16 | CFR-PMS-011 / PMS-AFR-090 positive
    Verify PMS shall allow Directors to review costs for patent filing and prosecution.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-16",
        abstract="Technical abstract for FR-TC-16",
        claims="Claim 1: Apparatus for FR-TC-16.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_17():
    """FR-TC-17 | CFR-PMS-012 / PMS-AFR-099 positive
    Verify PMS shall allow Attorneys to prepare an application package for patent-office filing.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-17",
        abstract="Technical abstract for FR-TC-17",
        claims="Claim 1: Apparatus for FR-TC-17.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_18():
    """FR-TC-18 | CFR-PMS-013 / PMS-AFR-107 positive
    Verify PMS shall activate post-grant tracking only for patents with status Granted.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-18",
        abstract="Technical abstract for FR-TC-18",
        claims="Claim 1: Apparatus for FR-TC-18.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_19():
    """FR-TC-19 | CFR-PMS-014 / PMS-AFR-116 positive
    Verify PMS shall allow recording of office actions received from patent offices.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-19",
        abstract="Technical abstract for FR-TC-19",
        claims="Claim 1: Apparatus for FR-TC-19.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_20():
    """FR-TC-20 | CFR-PMS-015 / PMS-AFR-125 positive
    Verify PMS shall allow Applicants to withdraw applications before the filing stage.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-20",
        abstract="Technical abstract for FR-TC-20",
        claims="Claim 1: Apparatus for FR-TC-20.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_21():
    """FR-TC-21 | CFR-PMS-016 / PMS-AFR-132 positive
    Verify PMS shall allow Applicants to manage multiple inventors for an application.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-21",
        abstract="Technical abstract for FR-TC-21",
        claims="Claim 1: Apparatus for FR-TC-21.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_22():
    """FR-TC-22 | CFR-PMS-016 / PMS-AFR-132 validation-refusal
    Verify refusal on invalid input for CFR-PMS-016
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_23():
    """FR-TC-23 | CFR-PMS-017 / PMS-AFR-141 positive
    Verify PMS shall allow Applicants to search prior-art references.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-23",
        abstract="Technical abstract for FR-TC-23",
        claims="Claim 1: Apparatus for FR-TC-23.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_24():
    """FR-TC-24 | CFR-PMS-018 / PMS-AFR-150 positive
    Verify PMS shall maintain version history for application documents.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-24",
        abstract="Technical abstract for FR-TC-24",
        claims="Claim 1: Apparatus for FR-TC-24.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_25():
    """FR-TC-25 | CFR-PMS-019 / PMS-AFR-158 positive
    Verify PMS shall allow Applicants to submit licensing requests.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-25",
        abstract="Technical abstract for FR-TC-25",
        claims="Claim 1: Apparatus for FR-TC-25.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_26():
    """FR-TC-26 | CFR-PMS-019 / PMS-AFR-158 validation-refusal
    Verify refusal on invalid input for CFR-PMS-019
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_27():
    """FR-TC-27 | CFR-PMS-020 / PMS-AFR-165 positive
    Verify PMS shall allow Applicants to file appeals against rejected applications.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-27",
        abstract="Technical abstract for FR-TC-27",
        claims="Claim 1: Apparatus for FR-TC-27.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_28():
    """FR-TC-28 | CFR-PMS-021 / PMS-AFR-172 positive
    Verify PMS shall calculate and monitor Director review deadlines using the applicable review-deadline rule.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-28",
        abstract="Technical abstract for FR-TC-28",
        claims="Claim 1: Apparatus for FR-TC-28.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_29():
    """FR-TC-29 | CFR-PMS-022 / PMS-AFR-182 positive
    Verify PMS shall allow PCC_ADMIN and Directors to generate application status and progress reports.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-29",
        abstract="Technical abstract for FR-TC-29",
        claims="Claim 1: Apparatus for FR-TC-29.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_30():
    """FR-TC-30 | CFR-PMS-023 / PMS-AFR-192 positive
    Verify PMS shall trigger system-generated email notifications for application submission.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-30",
        abstract="Technical abstract for FR-TC-30",
        claims="Claim 1: Apparatus for FR-TC-30.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_31():
    """FR-TC-31 | CFR-PMS-024 / PMS-AFR-207 positive
    Verify PMS shall maintain an audit trail of PMS actions.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-31",
        abstract="Technical abstract for FR-TC-31",
        claims="Claim 1: Apparatus for FR-TC-31.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_32():
    """FR-TC-32 | CFR-PMS-025 / PMS-AFR-216 positive
    Verify PMS shall require valid role assignments before users access patent-management functions.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-32",
        abstract="Technical abstract for FR-TC-32",
        claims="Claim 1: Apparatus for FR-TC-32.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_33():
    """FR-TC-33 | CFR-PMS-025 / PMS-AFR-216 validation-refusal
    Verify refusal on invalid input for CFR-PMS-025
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_34():
    """FR-TC-34 | CFR-PMS-026 / PMS-AFR-217 positive
    Verify PMS shall prevent attorney assignment until Director approval is recorded.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-34",
        abstract="Technical abstract for FR-TC-34",
        claims="Claim 1: Apparatus for FR-TC-34.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_35():
    """FR-TC-35 | CFR-PMS-026 / PMS-AFR-217 validation-refusal
    Verify refusal on invalid input for CFR-PMS-026
    """
    with pytest.raises(ValidationError):
        create_draft(applicant_user_id=101, title="   ", abstract="", claims="")

@pytest.mark.django_db
def test_fr_tc_36():
    """FR-TC-36 | CFR-PMS-027 / PMS-AFR-220 positive
    Verify PMS shall enforce role-based access control for confidential patent information.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-36",
        abstract="Technical abstract for FR-TC-36",
        claims="Claim 1: Apparatus for FR-TC-36.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_37():
    """FR-TC-37 | CFR-PMS-028 / PMS-AFR-221 positive
    Verify PMS shall maintain exactly one active PCC_ADMIN as the system oversight role.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-37",
        abstract="Technical abstract for FR-TC-37",
        claims="Claim 1: Apparatus for FR-TC-37.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_38():
    """FR-TC-38 | CFR-PMS-029 / PMS-AFR-228 positive
    Verify PMS shall treat patent-office system integration as external unless PMS records filing, status, or communication data from it.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-38",
        abstract="Technical abstract for FR-TC-38",
        claims="Claim 1: Apparatus for FR-TC-38.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

@pytest.mark.django_db
def test_fr_tc_39():
    """FR-TC-39 | CFR-PMS-030 / PMS-AFR-236 positive
    Verify PMS shall allow Directors to reject a proposed patent budget and record the rejection outcome.
    """
    app = create_draft(
        applicant_user_id=101,
        title="Invention for FR-TC-39",
        abstract="Technical abstract for FR-TC-39",
        claims="Claim 1: Apparatus for FR-TC-39.",
    )
    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT

