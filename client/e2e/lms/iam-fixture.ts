import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const iam = resolve(process.env.E2E_IAM_DIR ?? resolve(here, "../../../../Fusion_System_Administrator"));
const source = "e2e:lms-course-refusal";

function manage(code: string) {
  const env = Object.fromEntries(Object.entries(process.env)
    .filter(([key]) => key !== "DJANGO_SETTINGS_MODULE" && !key.startsWith("DB_")));
  return execFileSync(resolve(iam, "Backend/venv/bin/python"), ["manage.py", "shell", "-c", code], {
    cwd: resolve(iam, "Backend/backend"), env, encoding: "utf8", stdio: "pipe",
  }).trim().split("\n").at(-1) ?? "";
}

export function grantModuleWithoutCoursePermission() {
  const result = JSON.parse(manage(`
import json
from iam.models import IamDesignationModule, RolePermission
assert not RolePermission.objects.filter(designation="placement_officer", permission="lms.course.view").exists()
row, created = IamDesignationModule.objects.get_or_create(designation="placement_officer", module_code="lms", source="${source}")
print(json.dumps({"id": row.pk, "created": created}))
`)) as { id: number; created: boolean };
  if (!Number.isInteger(result.id) || result.id < 1) throw new Error("Invalid fixture grant ID");
  return () => {
    if (result.created) manage(`from iam.models import IamDesignationModule; IamDesignationModule.objects.filter(pk=${result.id}, source="${source}").delete()`);
  };
}
