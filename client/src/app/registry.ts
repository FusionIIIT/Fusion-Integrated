/** Frontend module registry; module code must match IAM's accesscontrol_module.code. */
import type { RouteObject } from "react-router-dom";

export interface ModuleManifest {
  code: string;
  basePath: string;
  load: () => Promise<{ routes: RouteObject[] }>;
}

export const MODULE_REGISTRY: Record<string, ModuleManifest> = {
  placement_cell: {
    code: "placement_cell",
    basePath: "/placement",
    load: () => import("../modules/placement/routes"),
  },
  elm: {
    code: "elm",
    basePath: "/elm",
    load: () => import("../modules/elm/routes"),
  },
};
