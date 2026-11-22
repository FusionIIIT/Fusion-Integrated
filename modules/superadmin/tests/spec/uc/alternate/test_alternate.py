from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.uc._cases import run_case

pytestmark = pytest.mark.django_db























def test_tc_061_uc(sa_principal, it_principal, stub_iam):
    """TC-061; source_id: UC-SA-017 Alternative A1."""
    run_case("TC-061", sa_principal, it_principal, stub_iam)








def test_tc_083_uc(sa_principal, it_principal, stub_iam):
    """TC-083; source_id: UC-SA-024 Alternative A1."""
    run_case("TC-083", sa_principal, it_principal, stub_iam)








def test_tc_105_uc(sa_principal, it_principal, stub_iam):
    """TC-105; source_id: UC-SA-031 Alternative A1."""
    run_case("TC-105", sa_principal, it_principal, stub_iam)
