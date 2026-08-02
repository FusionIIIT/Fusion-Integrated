"""The module registry — what modules exist and where they live in the UI.

A module is a ROW here, not a boolean column keyed by a designation name as in
the legacy ModuleAccess table, so adding one is an insert rather than a schema
migration and renaming a role cannot silently break access. Who may enter is
IAM's decision and arrives in the token.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class Module(TimeStampedModel):
    STATUS = [("planned", "Planned"), ("active", "Active"),
              ("deprecated", "Deprecated")]

    code = models.CharField(max_length=48, unique=True)      # placement_cell
    label = models.CharField(max_length=80)                  # "Placement Cell"
    icon = models.CharField(max_length=48, default="FaCircle")
    base_path = models.CharField(max_length=80)              # /placement
    nav_section = models.CharField(max_length=48, default="Modules")
    sort_order = models.PositiveSmallIntegerField(default=100)
    status = models.CharField(max_length=16, choices=STATUS, default="planned")

    class Meta:
        db_table = "accesscontrol_module"
        ordering = ["nav_section", "sort_order", "label"]

    def __str__(self) -> str:
        return self.code


class NavItem(TimeStampedModel):
    """A link inside a module. Hidden unless the caller holds
    `required_permission`, so two roles can share a module and still see
    different menus."""

    module = models.ForeignKey(Module, on_delete=models.CASCADE,
                               related_name="nav_items")
    code = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=80)
    icon = models.CharField(max_length=48, default="FaCircle")
    to = models.CharField(max_length=160)
    required_permission = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "accesscontrol_nav_item"
        ordering = ["sort_order", "label"]

    def __str__(self) -> str:
        return self.code
