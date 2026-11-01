"""Make the ERP's tables exist while tests run."""
from __future__ import annotations

import sys

from django.db import connections
from django.db.models.signals import pre_migrate

_built: set[str] = set()


def _models():
    """Every unmanaged model shadowing an ERP table.

    Named by module rather than by `managed is False` alone, so a new shadow
    module is an explicit decision instead of something tests silently start
    creating tables for.
    """
    from django.apps import apps

    from api.models import batches, erp

    shadows = {erp.__name__, batches.__name__}
    return [
        model
        # create_model builds a model's own M2M tables, so skip auto-created ones.
        for model in apps.get_app_config("api").get_models()
        if not model._meta.managed and model.__module__ in shadows
    ]


def create_erp_tables(using: str = "default") -> None:
    """Idempotent, and quiet if the tables are already there."""
    if using in _built:
        return
    connection = connections[using]
    existing = set(connection.introspection.table_names())
    with connection.schema_editor() as editor:
        for model in _models():
            if model._meta.db_table not in existing:
                editor.create_model(model)
    _built.add(using)


def _on_pre_migrate(sender, **kwargs):
    using = kwargs.get("using", "default")
    if using != "default":
        return                      # the ERP is only ever the default alias
    create_erp_tables(using)


def install_for_tests() -> None:
    """Connect the hook, but only for a test run."""
    if "test" not in sys.argv[1:2]:
        return
    pre_migrate.connect(_on_pre_migrate, dispatch_uid="iam.create_erp_tables")
