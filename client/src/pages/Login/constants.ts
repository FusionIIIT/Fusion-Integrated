/**
 * Login constants, ported from Fusion_System_Administrator. Only the subtitle
 * tag differs, so a person can tell at a glance which door they are at.
 */
export const CONFIG = Object.freeze({
  MOBILE_BREAKPOINT: 768,
  // Throttle mouse tracking so the decorative glow can't flood React.
  MOUSE_THROTTLE_MS: 50,
  SHAKE_DURATION_MS: 500,
  POST_LOGIN_ROUTE: "/",
});

/** The tag under the institute name. This is the ONE thing that differs from
 *  the operator console's header. */
export const SURFACE_TAG = "FUSION · INTEGRATED";
export const RECRUITER_SURFACE_TAG = "FUSION · RECRUITER PORTAL";

export { BRAND } from "../../ui/theme/theme";
