import type { ModuleManifest } from "../../app/registry";

export const manifest: ModuleManifest = {
  code: "elm",
  basePath: "/elm",
  load: () => import("./routes"),
};
