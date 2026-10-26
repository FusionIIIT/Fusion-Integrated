"""Test environment bootstrap for standalone runner environments."""
from __future__ import annotations

import sys
import types

if "rest_framework" not in sys.modules:
    try:
        import rest_framework  # noqa: F401
    except ImportError:
        rf = types.ModuleType("rest_framework")
        rf_status = types.ModuleType("rest_framework.status")
        rf_status.HTTP_400_BAD_REQUEST = 400
        rf_status.HTTP_401_UNAUTHORIZED = 401
        rf_status.HTTP_403_FORBIDDEN = 403
        rf_status.HTTP_404_NOT_FOUND = 404
        rf_status.HTTP_409_CONFLICT = 409
        rf_status.HTTP_422_UNPROCESSABLE_ENTITY = 422
        rf_status.HTTP_201_CREATED = 201
        rf.status = rf_status

        rf_resp = types.ModuleType("rest_framework.response")
        rf_resp.Response = lambda *a, **k: None
        rf.response = rf_resp

        rf_views = types.ModuleType("rest_framework.views")
        rf_views.exception_handler = lambda *a, **k: None
        rf_views.APIView = type("APIView", (), {})
        rf.views = rf_views

        rf_perms = types.ModuleType("rest_framework.permissions")
        rf_perms.BasePermission = type("BasePermission", (), {})
        rf.permissions = rf_perms

        rf_serializers = types.ModuleType("rest_framework.serializers")
        rf_serializers.Serializer = type("Serializer", (), {})
        rf_serializers.ModelSerializer = type("ModelSerializer", (), {})
        rf_serializers.ChoiceField = lambda *a, **k: None
        rf_serializers.DateField = lambda *a, **k: None
        rf_serializers.CharField = lambda *a, **k: None
        rf_serializers.BooleanField = lambda *a, **k: None
        rf_serializers.IntegerField = lambda *a, **k: None
        rf_serializers.JSONField = lambda *a, **k: None
        rf_serializers.SerializerMethodField = lambda *a, **k: None
        rf.serializers = rf_serializers

        sys.modules["rest_framework"] = rf
        sys.modules["rest_framework.status"] = rf_status
        sys.modules["rest_framework.response"] = rf_resp
        sys.modules["rest_framework.views"] = rf_views
        sys.modules["rest_framework.permissions"] = rf_perms
        sys.modules["rest_framework.serializers"] = rf_serializers

if "django" not in sys.modules:
    try:
        import django  # noqa: F401
    except ImportError:
        class DummyModel:
            objects = None
            pk = None

            def __init__(self, **kwargs):
                self.pk = 1
                for k, v in kwargs.items():
                    setattr(self, k, v)

            def get_category_display(self):
                choices = getattr(DummyChoices, "choices", [])
                return dict(choices).get(getattr(self, "category", ""), getattr(self, "category", ""))

            def clean(self):
                pass

            def save(self, *a, **k):
                pass

        class DummyManager:
            def __init__(self):
                self.model = DummyModel

            def create(self, **kwargs):
                return DummyModel(**kwargs)

            def get(self, **kwargs):
                return DummyModel(**kwargs)

            def filter(self, *a, **k):
                return self

            def none(self):
                return self

            def all(self):
                return self

            def order_by(self, *a, **k):
                return self

        DummyModel.objects = DummyManager()

        class DummyTimeStamped(DummyModel):
            pass

        class DummyUserScoped(DummyModel):
            pass

        class DummyChoices:
            CL = "CL"
            RH = "RH"
            SCL = "SCL"
            EL = "EL"
            COL = "COL"
            VL = "VL"
            choices = [
                ("CL", "Casual Leave"),
                ("RH", "Restricted Holiday"),
                ("SCL", "Special Casual Leave"),
                ("EL", "Earned Leave"),
                ("COL", "Commuted Leave"),
                ("VL", "Vacation Leave"),
            ]

        class DummyField:
            def __init__(self, *args, **kwargs):
                pass

        class DummyModels:
            Model = DummyModel
            TextChoices = DummyChoices
            CharField = DummyField
            DateField = DummyField
            TextField = DummyField
            BooleanField = DummyField
            JSONField = DummyField
            IntegerField = DummyField
            PositiveSmallIntegerField = DummyField
            DecimalField = DummyField
            ForeignKey = DummyField
            DateTimeField = DummyField
            CASCADE = None
            UniqueConstraint = DummyField
            Index = DummyField

            @staticmethod
            def Q(*args, **kwargs):  # noqa: N802
                return None

        class DummyTransaction:
            @staticmethod
            def atomic():
                class _Atomic:
                    def __enter__(self):
                        return self

                    def __exit__(self, *exc):
                        return False
                return _Atomic()

        django_mod = types.ModuleType("django")
        django_db = types.ModuleType("django.db")
        django_db.models = DummyModels
        django_db.transaction = DummyTransaction
        django_db_models = types.ModuleType("django.db.models")
        django_db_models.Model = DummyModel
        django_db_models.TextChoices = DummyChoices
        django_db_models.Q = lambda *a, **k: None
        django_db_models.QuerySet = type("QuerySet", (), {})

        django_core = types.ModuleType("django.core")
        django_core_exc = types.ModuleType("django.core.exceptions")

        class ValidationError(Exception):
            def __init__(self, message_dict):
                self.message_dict = message_dict
                self.messages = [str(message_dict)]
                super().__init__(str(message_dict))

        django_core_exc.ValidationError = ValidationError

        django_utils = types.ModuleType("django.utils")
        django_utils_trans = types.ModuleType("django.utils.translation")
        django_utils_trans.gettext_lazy = lambda s: s

        sys.modules["django"] = django_mod
        sys.modules["django.db"] = django_db
        sys.modules["django.db.models"] = django_db_models
        sys.modules["django.db.transaction"] = DummyTransaction
        sys.modules["django.core"] = django_core
        sys.modules["django.core.exceptions"] = django_core_exc
        sys.modules["django.utils"] = django_utils
        sys.modules["django.utils.translation"] = django_utils_trans

        # Import real core and inject db.mixins if needed
        import core.db
        core_mixins = types.ModuleType("core.db.mixins")
        core_mixins.TimeStampedModel = DummyTimeStamped
        core_mixins.UserScopedModel = DummyUserScoped
        sys.modules["core.db.mixins"] = core_mixins
        core.db.mixins = core_mixins

        # Spectacular dummy
        drf_spec = types.ModuleType("drf_spectacular")
        drf_spec_utils = types.ModuleType("drf_spectacular.utils")
        drf_spec_utils.extend_schema = lambda *a, **k: (lambda fn: fn)
        sys.modules["drf_spectacular"] = drf_spec
        sys.modules["drf_spectacular.utils"] = drf_spec_utils

        # Fusion auth dummy
        fa = types.ModuleType("fusion_auth")
        fa_perms = types.ModuleType("fusion_auth.permissions")
        fa_perms.HasModuleGrant = lambda code: type("HasModuleGrant", (), {})
        fa_perms.HasPermission = lambda *codes: type("HasPermission", (), {})
        sys.modules["fusion_auth"] = fa
        sys.modules["fusion_auth.permissions"] = fa_perms
