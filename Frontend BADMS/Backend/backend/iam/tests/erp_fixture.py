"""A real ERP schema, in the test database."""
from __future__ import annotations

import random

from django.test import TestCase

from api.models.erp import (
    AuthUser,
    GlobalsDepartmentinfo,
    GlobalsDesignation,
    GlobalsExtrainfo,
    GlobalsHoldsdesignation,
)

DEPARTMENTS = ("CSE", "ECE", "ME", "Design", "Natural Science", "Registrar Office")
DESIGNATIONS = (
    "Professor", "Associate Professor", "Assistant Professor",
    "Junior Assistant", "Senior Assistant", "Registrar", "HOD (CSE)", "acadadmin",
)


class ErpSchemaTestCase(TestCase):
    """A TestCase with the ERP tables present."""

    databases = {"default", "system_db"}

    # The tables themselves are built before migrations, by iam.testing.


class ErpFactory:
    """Synthetic people, deterministic when seeded."""

    def __init__(self, seed: int = 0) -> None:
        self.random = random.Random(seed)
        self.next_id = 1000
        self.departments: dict[str, GlobalsDepartmentinfo] = {}
        self.designations: dict[str, GlobalsDesignation] = {}

    # -- building blocks -------------------------------------------------------
    def department(self, name: str) -> GlobalsDepartmentinfo:
        if name not in self.departments:
            self.departments[name] = GlobalsDepartmentinfo.objects.create(name=name)
        return self.departments[name]

    def designation(self, name: str) -> GlobalsDesignation:
        if name not in self.designations:
            self.designations[name] = GlobalsDesignation.objects.create(
                name=name, full_name=name, type="academic", basic=False)
        return self.designations[name]

    def _id(self) -> int:
        self.next_id += 1
        return self.next_id

    # -- the four shapes that matter ------------------------------------------
    def account(self, *, username: str | None = None, active: bool = True) -> AuthUser:
        """An auth_user row and nothing else: no profile, no designation."""
        uid = self._id()
        return AuthUser.objects.create(
            id=uid, username=username or f"u{uid}", password="pbkdf2$fake",
            first_name="Test", last_name=f"Person{uid}",
            email=f"u{uid}@example.invalid", is_active=active,
            is_staff=False, is_superuser=False,
            date_joined="2020-01-01T00:00:00Z")

    def employee(self, *, kind: str = "staff", department: str | None = None,
                 designation: str | None = None, active: bool = True) -> AuthUser:
        """An account with a profile, and optionally an office."""
        user = self.account(active=active)
        self._profile(user, kind, department)
        if designation:
            self.holds(user, designation)
        return user

    def student(self, *, roll_no: str | None = None) -> AuthUser:
        user = self.account(username=roll_no)
        self._profile(user, "student", "CSE")
        return user

    def _profile(self, user: AuthUser, kind: str,
                 department: str | None) -> GlobalsExtrainfo:
        """Every NOT NULL column filled, read off the model rather than guessed."""
        return GlobalsExtrainfo.objects.create(
            id=user.username,
            user_id=user.id,
            user_type=kind,
            department=self.department(department) if department else None,
            title="Dr." if kind == "faculty" else "Mr.",
            sex=self.random.choice("MF"),
            date_of_birth="1985-01-01",
            user_status="PRESENT",
            address=f"{self._id()} Test Street",
            about_me="",
            phone_no=9000000000 + self.next_id,
        )

    def holds(self, user: AuthUser, designation: str) -> GlobalsHoldsdesignation:
        """A designation, recorded the way the ERP records it."""
        return GlobalsHoldsdesignation.objects.create(
            user_id=user.id, working_id=user.id,
            designation=self.designation(designation))

    # -- a whole institute -----------------------------------------------------
    def institute(self, *, employees: int = 20, students: int = 10,
                  orphans: int = 3) -> dict[str, list[AuthUser]]:
        """A plausible mix, including the shapes that caused real defects."""
        made: dict[str, list[AuthUser]] = {
            "faculty": [], "staff": [], "students": [], "orphans": [],
        }
        for i in range(employees):
            kind = "faculty" if i % 2 == 0 else "staff"
            made[kind].append(self.employee(
                kind=kind,
                department=self.random.choice(DEPARTMENTS),
                designation=self.random.choice(DESIGNATIONS) if i % 3 else None,
            ))
        for i in range(students):
            made["students"].append(self.student(roll_no=f"24BCS{i:03d}"))
        # No profile, no designation: the rows that used to be called staff.
        made["orphans"] = [self.account() for _ in range(orphans)]
        return made
