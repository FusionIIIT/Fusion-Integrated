"""PC-UC-014: every company registration gets its own slug, even when two race for one."""
import threading

import pytest
from django.db import IntegrityError, connection

from core.api.exceptions import ConflictError
from modules.placement.models import Company
from modules.placement.services import companies


@pytest.mark.django_db
def test_pc_uc_014_two_names_that_slug_alike_each_get_their_own_slug():
    # PC-UC-014
    first = companies.register(name="Acme Corp")
    second = companies.register(name="Acme-Corp")
    assert (first.slug, second.slug) == ("acme-corp", "acme-corp-2")


@pytest.mark.django_db(transaction=True)
def test_pc_uc_014_two_registrations_racing_for_one_slug_both_succeed(monkeypatch):
    # PC-UC-014: both threads choose a slug before either inserts.
    both_chose = threading.Barrier(2, timeout=10)
    chose_once = threading.local()
    choose = companies._unique_slug

    def choose_then_wait(name):
        slug = choose(name)
        if not getattr(chose_once, "done", False):
            chose_once.done = True
            both_chose.wait()
        return slug

    monkeypatch.setattr(companies, "_unique_slug", choose_then_wait)
    slugs, failures = [], []

    names = iter(("Acme Corp", "Acme-Corp"))

    def register(name):
        try:
            slugs.append(companies.register(name=name).slug)
        except (IntegrityError, ConflictError) as exc:
            failures.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=register, args=(next(names),)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert failures == []
    assert sorted(slugs) == ["acme-corp", "acme-corp-2"]
    assert Company.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_pc_uc_014_two_registrations_racing_for_one_name_leave_one_company(monkeypatch):
    # PC-UC-014: both pass the name check before either inserts; the index refuses one.
    both_checked = threading.Barrier(2, timeout=10)
    waited = threading.local()
    choose = companies._unique_slug

    def wait_then_choose(name):
        if not getattr(waited, "done", False):
            waited.done = True
            both_checked.wait()
        return choose(name)

    monkeypatch.setattr(companies, "_unique_slug", wait_then_choose)
    codes = []

    def register():
        try:
            companies.register(name="Acme Corp")
            codes.append("created")
        except ConflictError as exc:
            codes.append(exc.code)
        finally:
            connection.close()

    threads = [threading.Thread(target=register) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(codes) == ["company_exists", "created"]
    assert Company.objects.filter(name="Acme Corp").count() == 1


@pytest.mark.django_db
def test_pc_uc_014_a_slug_that_keeps_clashing_is_refused_with_409(monkeypatch):
    # PC-UC-014
    Company.objects.create(name="Acme-Corp", slug="acme-corp", status="prospect")
    monkeypatch.setattr(companies, "_unique_slug", lambda name: "acme-corp")

    with pytest.raises(ConflictError) as raised:
        companies.register(name="Acme Corp")

    assert raised.value.code == "company_slug_contention"
    assert raised.value.status_code == 409
    assert not Company.objects.filter(name="Acme Corp").exists()


@pytest.mark.django_db
class TestSelfRegistration:
    URL = "/api/v1/placement/companies/register"
    BODY = {"name": "Acme Robotics", "sector": "Robotics", "hq_city": "Pune",
            "contact_name": "R. Mehta", "contact_email": "hiring@acme.example"}

    def test_pc_uc_014_a_company_submits_its_own_registration_and_it_waits_for_approval(self):
        # PC-AFR-044, PC-BR-007, PC-UC-014, PC-CFR-014
        from rest_framework.test import APIClient
        r = APIClient().post(self.URL, self.BODY, format="json")
        assert r.status_code == 201
        company = Company.objects.get(name="Acme Robotics")
        assert (company.approval_status, company.status) == ("pending", "prospect")
        assert company.contacts.get().email == "hiring@acme.example"
        assert not company.can_operate

    def test_pc_uc_014_e1_missing_contact_records_nothing(self):
        # PC-UC-014
        from rest_framework.test import APIClient
        body = {k: v for k, v in self.BODY.items() if k != "contact_email"}
        r = APIClient().post(self.URL, body, format="json")
        assert r.status_code == 400
        assert not Company.objects.exists()

    def test_pc_uc_014_a_blank_name_records_nothing(self):
        # PC-UC-014
        from rest_framework.test import APIClient
        r = APIClient().post(self.URL, {**self.BODY, "name": "   "}, format="json")
        assert r.status_code in (400, 409)
        assert not Company.objects.exists()

    def test_pc_afr_045_a_pending_company_gets_no_placement_function_until_approved(self):
        # PC-BR-007: approval is recorded by the office; operation follows it., PC-AFR-045
        company = companies.register(name="Bolt", contact={"name": "A", "email": "a@b.c"})
        assert not company.can_operate
        approver = type("Officer", (), {"user_id": 62, "kind": "staff",
                                        "has_permission": lambda self, c: True})()
        approved = companies.approve(company_id=company.pk, actor=approver)
        assert approved.can_operate
        assert approved.approved_by_user_id == 62
