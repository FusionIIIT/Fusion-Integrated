"""BR-EL-016 to 020: Unit Head and sanction route resolution, and hierarchy validation."""
import pytest

from modules.leave.domain import routing as r

H = r.Hierarchy(
    units={"CSE": r.OrgUnit("CSE", "HOD (CSE)", "Director"),
           "ME": r.OrgUnit("ME", "HOD (ME)")},
    routes=(r.SanctionRoute("Director", "Deputy Registrar", employee_kind="faculty"),
            r.SanctionRoute("Registrar", "Deputy Registrar", employee_kind="staff"),
            r.SanctionRoute("Dean_s", "", employee_kind="faculty", category="SCL"),
            r.SanctionRoute("Director", "", applicant_designation="Registrar")))


def test_unit_head_for_an_ordinary_member():
    assert r.unit_head(H, department="CSE", roles=["faculty"]) == "HOD (CSE)"


def test_unit_heads_own_leave_goes_to_the_configured_reviewer():
    assert r.unit_head(H, department="CSE", roles=["faculty", "HOD (CSE)"]) == "Director"


def test_unit_head_with_no_reviewer_for_their_own_leave_is_refused():
    with pytest.raises(r.RoutingUnresolved):
        r.unit_head(H, department="ME", roles=["faculty", "HOD (ME)"])


def test_unmapped_unit_is_refused_with_its_name():
    with pytest.raises(r.RoutingUnresolved, match="IWD"):
        r.unit_head(H, department="IWD", roles=["staff"])


def test_most_specific_route_wins():
    assert r.sanction_route(H, kind="faculty", category="SCL", department="CSE",
                            roles=["faculty"]).sanction_designation == "Dean_s"
    assert r.sanction_route(H, kind="faculty", category="EL", department="CSE",
                            roles=["faculty"]).sanction_designation == "Director"


def test_designation_route_beats_kind_route():
    route = r.sanction_route(H, kind="staff", category="EL", department="Registrar Office",
                             roles=["staff", "Registrar"])
    assert route.sanction_designation == "Director"


def test_a_route_that_reaches_the_applicant_is_refused():
    h = r.Hierarchy(units={}, routes=(r.SanctionRoute("Registrar", "Deputy Registrar"),))
    with pytest.raises(r.RoutingUnresolved):
        r.sanction_route(h, kind="staff", category="EL", department="", roles=["Deputy Registrar"])


def test_no_route_is_refused():
    with pytest.raises(r.RoutingUnresolved):
        r.sanction_route(r.Hierarchy({}, ()), kind="staff", category="EL", department="",
                         roles=[])


def test_validation_requires_the_step_permission():
    bad = r.Hierarchy(units={"CSE": r.OrgUnit("CSE", "student", "HOD (CSE)")},
                      routes=(r.SanctionRoute("HOD (CSE)", "Registrar", category="CL"),
                              r.SanctionRoute("Director", employee_kind="alumni")))
    problems = r.validate(bad, reviewers=frozenset({"HOD (CSE)", "Director"}),
                          establishments=frozenset({"Deputy Registrar"}),
                          authorities=frozenset({"Director", "Registrar"}))
    text = " ".join(problems)
    for needle in ("'student' cannot review", "'HOD (CSE)' cannot sanction",
                   "'Registrar' cannot perform the Establishment", "'alumni'",
                   "not a higher-sanction"):
        assert needle in text


def test_director_flag():
    assert r.is_director(["faculty", "Director"])
    assert not r.is_director(["faculty"])
