/** Frontend module registry.
 *
 * `code` MUST match accesscontrol_module.code on the server.
 */
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
  quiz: {
    code: "quiz",
    basePath: "/quiz",
    load: () => import("../modules/quiz/routes"),
  },
};
