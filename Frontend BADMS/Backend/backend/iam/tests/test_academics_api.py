"""Who may read a CPI.

A CPI is sensitive academic data (PC-BR-023). The rules under test:
  * a peer service may read in bulk  — that is the platform's eligibility sweep
  * a signed-in student may read one row, their own
  * asking about someone else returns EMPTY, not 403 — a 403 would confirm the
    id exists and carries a declared result, which is itself a disclosure
"""
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from rest_framework.test import APITestCase

from iam.models import IamServiceToken, IamToken, IamUser, IamUserAcademic

URL = "/api/iam/v1/academics/standings"


class AcademicStandingApiTests(APITestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        for uid, name in ((1, "21BCS002"), (2, "21BCS003"), (3, "staffer")):
            IamUser.objects.create(erp_user_id=uid, username=name,
                                   display_name=name,
                                   kind="student" if uid < 3 else "staff",
                                   password_hash=make_password("pw"))
        for uid, roll, cpi in ((1, "21BCS002", "8.4"), (2, "21BCS003", "6.1")):
            IamUserAcademic.objects.create(
                erp_user_id=uid, roll_no=roll, cpi=Decimal(cpi),
                earned_credits=Decimal("100"),
                cpi_denominator_credits=Decimal("96"),
                active_backlogs=0, courses_counted=30, semester=5,
                semester_type="Odd Semester", declared_seq=50,
                programme="B.Tech", computed_by="iam-replica/v1")
        _, self.svc = IamServiceToken.issue("fusion-integrated")
        self.student = IamToken.issue(erp_user_id=1, username="21BCS002")
        self.other = IamToken.issue(erp_user_id=2, username="21BCS003")

    def get(self, ids, auth):
        return self.client.get(f"{URL}?ids={ids}", HTTP_AUTHORIZATION=auth)

    # -- the service path -------------------------------------------------
    def test_a_service_may_read_in_bulk(self):
        r = self.get("1,2", f"Service {self.svc}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual({row["user_id"] for row in r.json()["results"]}, {1, 2})

    def test_the_payload_carries_its_provenance(self):
        row = self.get("1", f"Service {self.svc}").json()["results"][0]
        for key in ("cpi", "semester", "semester_type", "declared_seq",
                    "computed_by", "synced_at", "active_backlogs"):
            self.assertIn(key, row)
        self.assertEqual(row["cpi"], "8.4")

    def test_a_student_with_no_declared_result_is_absent_not_zero(self):
        r = self.get("1,3", f"Service {self.svc}")           # 3 has no standing
        self.assertEqual([row["user_id"] for row in r.json()["results"]], [1])

    # -- the student path -------------------------------------------------
    def test_a_student_may_read_their_own(self):
        r = self.get("1", f"Token {self.student.raw_key}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"][0]["cpi"], "8.4")

    def test_a_student_asking_for_someone_else_gets_nothing(self):
        r = self.get("2", f"Token {self.student.raw_key}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])

    def test_a_student_cannot_widen_the_batch_to_include_others(self):
        """The id list is filtered, not rejected — so smuggling their own id in
        alongside others still yields only their own row."""
        r = self.get("1,2,3", f"Token {self.student.raw_key}")
        self.assertEqual([row["user_id"] for row in r.json()["results"]], [1])

    def test_the_response_does_not_distinguish_absent_from_forbidden(self):
        """Both an id that has no standing and an id belonging to someone else
        return an empty list, so the endpoint is not an existence oracle."""
        forbidden = self.get("2", f"Token {self.student.raw_key}")
        nonexistent = self.get("999999", f"Token {self.student.raw_key}")
        self.assertEqual(forbidden.json(), nonexistent.json())

    # -- rejection --------------------------------------------------------
    def test_no_credential_is_rejected(self):
        self.assertEqual(self.client.get(f"{URL}?ids=1").status_code, 401)

    def test_a_revoked_service_credential_is_rejected(self):
        IamServiceToken.objects.update(is_active=False)
        self.assertEqual(self.get("1", f"Service {self.svc}").status_code, 401)

    def test_non_integer_ids_are_a_400(self):
        self.assertEqual(self.get("1,oops", f"Service {self.svc}").status_code, 400)

    def test_no_ids_returns_empty_without_a_query(self):
        r = self.client.get(URL, HTTP_AUTHORIZATION=f"Service {self.svc}")
        self.assertEqual(r.json()["results"], [])

    def test_the_id_list_is_capped(self):
        r = self.get(",".join(str(i) for i in range(1, 2000)),
                     f"Service {self.svc}")
        self.assertEqual(r.status_code, 200)


class SessionAcademicTests(APITestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        IamUser.objects.create(erp_user_id=1, username="21BCS002",
                               display_name="A", kind="student",
                               password_hash=make_password("pw"))
        IamUser.objects.create(erp_user_id=2, username="prof", display_name="P",
                               kind="faculty", password_hash=make_password("pw"))

    def me(self, uid, username):
        tok = IamToken.issue(erp_user_id=uid, username=username)
        return self.client.get("/api/iam/v1/me",
                               HTTP_AUTHORIZATION=f"Token {tok.raw_key}").json()

    def test_a_student_without_a_declared_result_has_no_academic_key(self):
        """Absent, not null — a consumer that forgets to check gets a KeyError
        rather than silently treating a missing CPI as zero."""
        self.assertNotIn("academic", self.me(1, "21BCS002"))

    def test_a_student_with_a_declared_result_carries_it_on_me(self):
        IamUserAcademic.objects.create(
            erp_user_id=1, roll_no="21BCS002", cpi=Decimal("7.2"),
            earned_credits=Decimal("80"), cpi_denominator_credits=Decimal("78"),
            active_backlogs=1, courses_counted=24, semester=4,
            semester_type="Even Semester", declared_seq=41, programme="B.Tech")
        payload = self.me(1, "21BCS002")
        self.assertEqual(payload["academic"]["cpi"], "7.2")
        self.assertEqual(payload["academic"]["active_backlogs"], 1)

    def test_a_non_student_never_carries_an_academic_block(self):
        self.assertNotIn("academic", self.me(2, "prof"))


class AcademicDirectoryTests(APITestCase):
    """The whole cohort's standing. The largest disclosure in the module, so
    the access rules get the most attention."""

    databases = {"default", "system_db"}
    URL = "/api/iam/v1/academics/directory"

    def setUp(self):
        rows = [
            (10, "21BCS001", "CSE", 2021, "B.Tech", "8.1"),
            (11, "21BCS002", "CSE", 2021, "B.Tech", None),      # undeclared
            (12, "22BEC010", "ECE", 2022, "B.Tech", "7.4"),
            (13, "21BDS005", "Des.", 2021, "B.Des", "9.0"),
        ]
        for uid, roll, disc, batch, prog, cpi in rows:
            IamUser.objects.create(
                erp_user_id=uid, username=roll, display_name=f"Student {roll}",
                kind="student", discipline=disc, batch_year=batch,
                programme=prog, password_hash=make_password("pw"))
            if cpi:
                IamUserAcademic.objects.create(
                    erp_user_id=uid, roll_no=roll, cpi=Decimal(cpi),
                    earned_credits=Decimal("100"),
                    cpi_denominator_credits=Decimal("96"), active_backlogs=0,
                    courses_counted=30, semester=5,
                    semester_type="Odd Semester", declared_seq=50,
                    programme=prog)
        # A member of staff must not appear in a STUDENT directory.
        IamUser.objects.create(erp_user_id=99, username="staffer",
                               display_name="Staff", kind="staff",
                               password_hash=make_password("pw"))
        _, self.svc = IamServiceToken.issue("placement")

    def get(self, query="", auth=None):
        return self.client.get(
            f"{self.URL}?{query}",
            HTTP_AUTHORIZATION=auth or f"Service {self.svc}")

    # -- access ------------------------------------------------------------
    def test_a_service_credential_may_enumerate(self):
        self.assertEqual(self.get().status_code, 200)

    def test_a_student_cannot_enumerate_the_cohort(self):
        """Even though they can read their OWN standing elsewhere. Listing
        everybody is a different question from looking one person up."""
        token = IamToken.issue(erp_user_id=10, username="21BCS001")
        self.assertEqual(self.get(auth=f"Token {token.raw_key}").status_code, 401)

    def test_no_credential_is_rejected(self):
        self.assertEqual(self.client.get(self.URL).status_code, 401)

    # -- content -----------------------------------------------------------
    def test_only_students_are_listed(self):
        rolls = {r["roll_no"] for r in self.get().json()["results"]}
        self.assertNotIn("staffer", rolls)
        self.assertEqual(len(rolls), 4)

    def test_an_undeclared_student_is_listed_with_a_null_cpi(self):
        """Listed, not omitted — the office needs to see who is missing a
        result. And null, not zero."""
        row = next(r for r in self.get().json()["results"]
                   if r["roll_no"] == "21BCS002")
        self.assertIsNone(row["cpi"])
        self.assertIsNone(row["semester"])

    def test_a_declared_row_carries_its_provenance(self):
        row = next(r for r in self.get().json()["results"]
                   if r["roll_no"] == "21BCS001")
        self.assertEqual(row["cpi"], "8.1")
        self.assertEqual(row["semester"], 5)
        self.assertEqual(row["semester_type"], "Odd Semester")

    # -- filters -----------------------------------------------------------
    def test_filter_by_discipline(self):
        body = self.get("discipline=CSE").json()
        self.assertEqual(body["count"], 2)

    def test_discipline_match_is_case_insensitive(self):
        self.assertEqual(self.get("discipline=cse").json()["count"], 2)

    def test_filter_by_batch(self):
        self.assertEqual(self.get("batch_year=2022").json()["count"], 1)

    def test_filter_by_programme(self):
        self.assertEqual(self.get("programme=B.Des").json()["count"], 1)

    def test_search_matches_roll_and_name(self):
        self.assertEqual(self.get("q=21BCS").json()["count"], 2)
        self.assertEqual(self.get("q=Student 22BEC010").json()["count"], 1)

    def test_filters_combine(self):
        self.assertEqual(self.get("discipline=CSE&batch_year=2021").json()["count"], 2)
        self.assertEqual(self.get("discipline=CSE&batch_year=2022").json()["count"], 0)

    def test_only_declared_narrows_the_query_not_the_page(self):
        """The count must reflect the filter. Filtering after slicing would
        report 2 CSE students and hand back a page containing one."""
        body = self.get("discipline=CSE&only_declared=true").json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["roll_no"], "21BCS001")

    # -- paging ------------------------------------------------------------
    def test_paging_reports_the_full_count(self):
        body = self.get("limit=2&offset=0").json()
        self.assertEqual(body["count"], 4)
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["limit"], 2)

    def test_the_page_size_is_capped(self):
        self.assertLessEqual(self.get("limit=9999").json()["limit"], 200)

    def test_a_non_integer_page_is_a_400(self):
        self.assertEqual(self.get("limit=lots").status_code, 400)
        self.assertEqual(self.get("batch_year=soon").status_code, 400)

    def test_ordering_is_stable(self):
        first = [r["roll_no"] for r in self.get("limit=4").json()["results"]]
        self.assertEqual(first, sorted(first))


class AcademicFiltersEndpointTests(APITestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        for uid, roll, disc, batch in ((1, "a", "CSE", 2021),
                                       (2, "b", "ECE", 2022),
                                       (3, "c", "CSE", 2022)):
            IamUser.objects.create(erp_user_id=uid, username=roll,
                                   display_name=roll, kind="student",
                                   discipline=disc, batch_year=batch,
                                   programme="B.Tech",
                                   password_hash=make_password("pw"))
        _, self.svc = IamServiceToken.issue("placement")

    def test_it_reports_what_is_actually_present(self):
        body = self.client.get("/api/iam/v1/academics/filters",
                               HTTP_AUTHORIZATION=f"Service {self.svc}").json()
        self.assertEqual(body["disciplines"], ["CSE", "ECE"])
        self.assertEqual(body["batch_years"], [2022, 2021])   # newest first
        self.assertEqual(body["programmes"], ["B.Tech"])
