from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db





def test_tc_059_workflow(sa_principal, it_principal, stub_iam):
    """TC-059; source_id: CFR-SA-011 / AFR-SA-049B."""
    run_case("TC-059", sa_principal, it_principal, stub_iam)


def test_tc_061_workflow(sa_principal, it_principal, stub_iam):
    """TC-061; source_id: CFR-SA-012 / AFR-SA-051A."""
    run_case("TC-061", sa_principal, it_principal, stub_iam)


def test_tc_062_workflow(sa_principal, it_principal, stub_iam):
    """TC-062; source_id: CFR-SA-012 / AFR-SA-051B."""
    run_case("TC-062", sa_principal, it_principal, stub_iam)





def test_tc_070_workflow(sa_principal, it_principal, stub_iam):
    """TC-070; source_id: CFR-SA-015 / AFR-SA-057."""
    run_case("TC-070", sa_principal, it_principal, stub_iam)






def test_tc_075_workflow(sa_principal, it_principal, stub_iam):
    """TC-075; source_id: CFR-SA-016 / AFR-SA-061A."""
    run_case("TC-075", sa_principal, it_principal, stub_iam)


def test_tc_076_workflow(sa_principal, it_principal, stub_iam):
    """TC-076; source_id: CFR-SA-016 / AFR-SA-061B."""
    run_case("TC-076", sa_principal, it_principal, stub_iam)
