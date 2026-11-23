from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.uc._cases import run_case

pytestmark = pytest.mark.django_db

















def test_tc_054_uc(sa_principal, it_principal, stub_iam):
    """TC-054; source_id: UC-SA-015 Exception E1."""
    run_case("TC-054", sa_principal, it_principal, stub_iam)





def test_tc_066_uc(sa_principal, it_principal, stub_iam):
    """TC-066; source_id: UC-SA-018 Exception E2."""
    run_case("TC-066", sa_principal, it_principal, stub_iam)





def test_tc_078_uc(sa_principal, it_principal, stub_iam):
    """TC-078; source_id: UC-SA-022 Exception E1."""
    run_case("TC-078", sa_principal, it_principal, stub_iam)


def test_tc_081_uc(sa_principal, it_principal, stub_iam):
    """TC-081; source_id: UC-SA-023 Exception E1."""
    run_case("TC-081", sa_principal, it_principal, stub_iam)



def test_tc_093_uc(sa_principal, it_principal, stub_iam):
    """TC-093; source_id: UC-SA-027 Exception E1."""
    run_case("TC-093", sa_principal, it_principal, stub_iam)
