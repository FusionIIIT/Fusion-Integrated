from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db













def test_tc_079_audit(sa_principal, it_principal, stub_iam):
    """TC-079; source_id: CFR-SA-018 / AFR-SA-064."""
    run_case("TC-079", sa_principal, it_principal, stub_iam)


def test_tc_083_audit(sa_principal, it_principal, stub_iam):
    """TC-083; source_id: CFR-SA-018 / AFR-SA-066."""
    run_case("TC-083", sa_principal, it_principal, stub_iam)









def test_tc_105_audit(sa_principal, it_principal, stub_iam):
    """TC-105; source_id: CFR-SA-017 / AFR-SA-081B."""
    run_case("TC-105", sa_principal, it_principal, stub_iam)
