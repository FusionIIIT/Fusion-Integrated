"""Seeding from the platform's manifest: authoritative for the modules it names, and nothing else."""
import json
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from iam import services
from iam.models import (IamDesignationModule, IamModule, IamNavItem,
                        RolePermission)


def manifest(grants, module="placement_cell", version=1, publisher="integrated"):
    return {"version": version, "publisher": publisher,
            "modules": {module: {"permissions": [], "system_permissions": [],
                                 "grants": grants}}}


class SeedPermissionsTests(TestCase):
    databases = {"default", "system_db"}

    def seed(self, payload, **kwargs):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "permissions.json"
            path.write_text(json.dumps(payload))
            out = StringIO()
            call_command("seed_iam_permissions", manifest=path, stdout=out,
                         **kwargs)
            return out.getvalue()

    def test_grants_in_the_manifest_are_created(self):
        self.seed(manifest({"student": ["placement_cell.registration.self"]}))
        self.assertTrue(RolePermission.objects.filter(
            designation="student",
            permission="placement_cell.registration.self").exists())

    def test_running_twice_changes_nothing(self):
        payload = manifest({"student": ["placement_cell.job_posting.view"]})
        self.seed(payload)
        self.assertIn("0 added, 0 revoked", self.seed(payload))
        self.assertEqual(RolePermission.objects.count(), 1)

    def test_a_grant_dropped_upstream_is_revoked(self):
        self.seed(manifest({"student": ["placement_cell.job_posting.view",
                                        "placement_cell.offer.issue"]}))
        self.seed(manifest({"student": ["placement_cell.job_posting.view"]}))
        self.assertEqual(
            [r.permission for r in RolePermission.objects.all()],
            ["placement_cell.job_posting.view"])

    def test_another_module_is_left_alone(self):
        """Scoped by permission prefix: seeding placement must not disarm hr."""
        RolePermission.objects.create(designation="hr_officer",
                                      permission="hr.employment.manage")
        self.seed(manifest({"student": ["placement_cell.job_posting.view"]}))
        self.assertTrue(RolePermission.objects.filter(
            permission="hr.employment.manage").exists())

    def test_dry_run_writes_nothing(self):
        out = self.seed(manifest({"student": ["placement_cell.offer.respond"]}),
                        dry_run=True)
        self.assertIn("1 to add", out)
        self.assertEqual(RolePermission.objects.count(), 0)

    def test_an_unknown_version_is_refused(self):
        with self.assertRaisesMessage(CommandError, "understands (1, 2)"):
            self.seed(manifest({"student": []}, version=99))

    def test_an_empty_manifest_is_not_taken_as_revoke_everything(self):
        RolePermission.objects.create(designation="student",
                                      permission="placement_cell.offer.respond")
        with self.assertRaisesMessage(CommandError, "lists no modules"):
            self.seed({"version": 1, "publisher": "integrated", "modules": {}})
        self.assertEqual(RolePermission.objects.count(), 1)

    def test_a_missing_manifest_says_how_to_make_one(self):
        with self.assertRaisesMessage(CommandError, "make permissions"):
            call_command("seed_iam_permissions",
                         manifest=Path("/nonexistent/permissions.json"),
                         stdout=StringIO())


class PublisherScopingTests(TestCase):
    databases = {"default", "system_db"}

    def seed(self, payload, **kwargs):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "permissions.json"
            path.write_text(json.dumps(payload))
            out = StringIO()
            call_command("seed_iam_permissions", manifest=path, stdout=out,
                         **kwargs)
            return out.getvalue()

    def grants(self, module, designations, publisher="integrated"):
        payload = manifest({}, module=module, publisher=publisher)
        payload["modules"][module]["module_grants"] = designations
        return payload

    def test_a_manifest_that_names_no_publisher_is_refused(self):
        payload = self.grants("leave", ["faculty"])
        del payload["publisher"]
        with self.assertRaises(CommandError):
            self.seed(payload)

    def test_each_publisher_writes_under_its_own_source(self):
        self.seed(self.grants("leave", ["faculty"], publisher="integrated"))
        self.seed(self.grants("students", ["student"], publisher="academic"))
        self.assertEqual(
            set(IamDesignationModule.objects.values_list("source", flat=True)),
            {"manifest:integrated", "manifest:academic"})

    def test_one_publisher_never_revokes_another_s_grants(self):
        """The whole point: two services, one shared IAM, no silent revoke."""
        self.seed(self.grants("leave", ["faculty"], publisher="integrated"))
        self.seed(self.grants("students", ["student"], publisher="academic"))
        self.assertTrue(IamDesignationModule.objects.filter(
            module_code="leave", designation="faculty").exists())

    def test_claiming_a_module_another_publisher_owns_is_refused(self):
        self.seed(self.grants("leave", ["faculty"], publisher="integrated"))
        with self.assertRaises(CommandError):
            self.seed(self.grants("leave", ["student"], publisher="academic"))

    def test_rows_seeded_before_publishers_existed_are_adopted(self):
        IamDesignationModule.objects.create(
            designation="faculty", module_code="leave",
            source=IamDesignationModule.MANIFEST)
        self.seed(self.grants("leave", ["faculty"], publisher="integrated"))
        row = IamDesignationModule.objects.get(module_code="leave")
        self.assertEqual(row.source, "manifest:integrated")


class NavPublicationTests(TestCase):
    databases = {"default", "system_db"}

    def seed(self, payload, **kwargs):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "permissions.json"
            path.write_text(json.dumps(payload))
            call_command("seed_iam_permissions", manifest=path,
                         stdout=StringIO(), **kwargs)

    def payload(self, module="leave", publisher="integrated", items=None,
                status="active", version=2):
        nav = {"label": module.title(), "icon": "FaCircle",
               "base_path": f"/{module}", "nav_section": "Work",
               "sort_order": 10, "status": status,
               "items": items if items is not None else [
                   {"code": f"{module}.a", "label": "A", "icon": "FaCircle",
                    "to": f"/{module}/a", "required_permission": "",
                    "sort_order": 10}]}
        p = manifest({}, module=module, publisher=publisher, version=version)
        p["modules"][module]["module_grants"] = ["faculty"]
        p["modules"][module]["nav"] = nav
        return p

    def test_nav_is_stored_with_the_app_that_serves_it(self):
        self.seed(self.payload())
        module = IamModule.objects.get(code="leave")
        self.assertEqual(module.app, "integrated")
        self.assertEqual(module.nav_items.count(), 1)

    def test_a_v1_manifest_leaves_existing_nav_alone(self):
        """Silence is not an instruction to empty somebody's sidebar."""
        self.seed(self.payload())
        self.seed(self.payload(version=1))
        self.assertTrue(IamModule.objects.filter(code="leave").exists())

    def test_a_dropped_nav_item_disappears(self):
        self.seed(self.payload())
        self.seed(self.payload(items=[]))
        self.assertEqual(IamNavItem.objects.count(), 0)

    def test_publishers_do_not_overwrite_each_other_s_nav(self):
        self.seed(self.payload(module="leave", publisher="integrated"))
        self.seed(self.payload(module="students", publisher="academic"))
        self.assertEqual(
            set(IamModule.objects.values_list("code", "app")),
            {("leave", "integrated"), ("students", "academic")})

    def test_a_planned_module_is_published_but_never_rendered(self):
        self.seed(self.payload(status="planned"))
        self.assertTrue(IamModule.objects.filter(code="leave").exists())
        self.assertEqual(services.build_navigation(["leave"], []), [])

    def test_navigation_spans_publishers_in_one_sidebar(self):
        self.seed(self.payload(module="leave", publisher="integrated"))
        self.seed(self.payload(module="students", publisher="academic"))
        nav = services.build_navigation(["leave", "students"], [])
        self.assertEqual([g["section"] for g in nav], ["Work"])
        self.assertEqual([i["app"] for i in nav[0]["items"]],
                         ["academic", "integrated"])

    def test_a_link_the_caller_may_not_use_is_not_drawn(self):
        self.seed(self.payload(items=[
            {"code": "leave.admin", "label": "Admin", "icon": "FaCircle",
             "to": "/leave/admin", "required_permission": "leave.policy.manage",
             "sort_order": 10}]))
        self.assertEqual(services.build_navigation(["leave"], []), [])

    def test_navigation_does_not_scale_its_queries_with_module_count(self):
        for i in range(6):
            self.seed(self.payload(module=f"m{i}", publisher=f"p{i}"))
        codes = [f"m{i}" for i in range(6)]
        with self.assertNumQueries(2, using="system_db"):
            services.build_navigation(codes, [])


class EmitRoutesTests(TestCase):
    databases = {"default", "system_db"}

    def _module(self, code, app, base, status="active"):
        return IamModule.objects.create(
            code=code, label=code.title(), base_path=base, nav_section="X",
            status=status, app=app, source=f"manifest:{app}")

    def emit(self, **kwargs):
        out = StringIO()
        call_command("emit_routes", nginx=True, stdout=out, **kwargs)
        return out.getvalue()

    def test_both_paths_come_from_the_base_path_not_the_code(self):
        """placement_cell is served at /placement; the code is not the path."""
        self._module("placement_cell", "integrated", "/placement")
        conf = self.emit()
        self.assertIn("location ^~ /placement/ {", conf)
        self.assertIn("location ^~ /api/v1/placement/ {", conf)
        self.assertNotIn("placement_cell/", conf)

    def test_a_planned_module_is_not_routed(self):
        self._module("hostel", "integrated", "/hostel", status="planned")
        self._module("leave", "integrated", "/leave")
        self.assertNotIn("/hostel/", self.emit())

    def test_an_app_with_no_upstream_is_refused(self):
        """Emitting it anyway would 404 every one of that app's paths."""
        self._module("curriculum", "academic", "/curriculum")
        with self.assertRaises(CommandError):
            self.emit()

    def test_two_modules_claiming_one_path_are_refused(self):
        self._module("a", "integrated", "/same")
        self._module("b", "legacy", "/same")
        with self.assertRaises(CommandError):
            self.emit()

    def test_routing_nothing_is_refused(self):
        with self.assertRaises(CommandError):
            self.emit()
