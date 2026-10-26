import type { ModuleManifest } from "../../app/registry";

export const manifest: ModuleManifest = {
  code: "leave_management",
  basePath: "/leave",
  load: () => import("./routes"),
};