import type { ModuleManifest } from "../../app/registry";

export const manifest: ModuleManifest = {
  code: "lms",
  basePath: "/lms",
  load: () => import("./routes"),
};
