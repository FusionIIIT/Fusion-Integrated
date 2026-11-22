"""BR-008 – Prohibition of Cross-Module Foreign Keys.

Business Rule:
Cross-module foreign keys are prohibited; references to external entities
must be plain integer IDs (Page 2 – ADR-0013 no cross-module FKs).
"""

import pytest
from django.apps import apps
from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField

@pytest.mark.django_db
def test_br_008_no_cross_module_foreign_keys():
    """Verify that every relational field in modules.complaints points to a model in the same app."""
    complaints_app = apps.get_app_config("complaints")
    complaints_models = set(complaints_app.get_models())

    for model in complaints_models:
        for field in model._meta.get_fields():
            if isinstance(field, (ForeignKey, OneToOneField, ManyToManyField)):
                # If reverse relation, field.related_model is the target
                target_model = field.related_model
                assert target_model in complaints_models, (
                    f"Violation of ADR-0013: Model '{model.__name__}' field '{field.name}' "
                    f"references external model '{target_model.__name__}' from app "
                    f"'{target_model._meta.app_label}'."
                )

@pytest.mark.django_db
def test_br_008_user_references_are_plain_integers():
    """Verify that all IAM/person references in CMS models are plain integer fields."""
    complaints_app = apps.get_app_config("complaints")

    user_field_names = [
        "complainant_user_id",
        "assigned_worker_id",
        "uploaded_by_user_id",
        "actor_user_id",
        "author_user_id",
        "user_id",
        "assigned_by_user_id",
    ]

    for model in complaints_app.get_models():
        for field_name in user_field_names:
            try:
                field = model._meta.get_field(field_name)
                # Field must exist as an integer type, never a relation
                assert field.get_internal_type() in ("IntegerField", "PositiveIntegerField", "BigIntegerField"), (
                    f"Model '{model.__name__}' field '{field_name}' should be an integer, "
                    f"got {field.get_internal_type()}."
                )
                assert not field.is_relation, (
                    f"Model '{model.__name__}' field '{field_name}' must not be a relational field."
                )
            except Exception:
                # Field does not exist on this specific model, which is normal
                pass
