import copy
import os
import tempfile
import uuid
import pytest
from django.conf import settings
from django.db import connections, connection
import django.apps

db_path = os.path.join(tempfile.gettempdir(), f"badms_uc_{uuid.uuid4().hex}.sqlite3")

d = copy.deepcopy(connections["default"].settings_dict)
d["ENGINE"] = "django.db.backends.sqlite3"
d["NAME"] = db_path
settings.DATABASES["default"] = d
connections.close_all()
del connections["default"]


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.django_db(transaction=True))


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            for app_label in ["contenttypes", "auth", "badms"]:
                try:
                    app_cfg = django.apps.apps.get_app_config(app_label)
                    for m in app_cfg.get_models():
                        try:
                            editor.create_model(m)
                        except Exception:
                            pass
                except Exception:
                    pass


@pytest.fixture
def make_quota():
    from modules.badms.models import StorageQuota

    def _make(user_id="user_1", quota_mb=1000, used_mb=0, department_id="CSE"):
        quota, _ = StorageQuota.objects.update_or_create(
            user_id=user_id,
            defaults={
                "department_id": department_id,
                "allocated_storage_mb": quota_mb,
                "used_storage_mb": used_mb,
            },
        )
        return quota

    return _make
