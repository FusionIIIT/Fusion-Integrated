/**
 * Login feature constants.
 *
 * Centralising tuning values, brand tokens and error mapping keeps the auth
 * components presentational and makes behaviour easy to adjust in one place as the
 * app grows.
 */

export const CONFIG = Object.freeze({
  MOBILE_BREAKPOINT: 768,
  // Throttle mouse tracking so the decorative glow can't flood React with renders.
  MOUSE_THROTTLE_MS: 50,
  // Fail fast rather than leaving the user staring at a spinner on a dead network.
  API_TIMEOUT_MS: 10_000,
  // Brief pause after success so the confirmation toast is seen before we redirect.
  AUTH_SUCCESS_DELAY_MS: 400,
  SHAKE_DURATION_MS: 500,
  // Where to land after a successful login.
  POST_LOGIN_ROUTE: "/dashboard",
});

/** Brand palette — mirrors the main Fusion client so the two apps feel like one. */
export const BRAND = Object.freeze({
  primary: "#15ABFF",
  dark: "#111111",
  danger: "#FA5252",
  surface: "#FFFFFF",
  surfaceAlt: "#F8F9FA",
  border: "#E9ECEF",
  gridLine: "#DEE2E6",
});

/**
 * Map any login error to a single user-facing message.
 *
 * Security note: for 400/401 we intentionally return one generic message and never
 * reveal whether the username or the password was wrong (avoids user enumeration).
 */
export function mapAuthError(err) {
  if (err?.code === "ECONNABORTED") {
    return "Request timed out. Check your connection and try again.";
  }
  if (err?.response) {
    const { status, data } = err.response;
    const serverMessage = data?.message || data?.error;
    if (status === 400 || status === 401) {
      return "Invalid username or password. Please try again.";
    }
    if (status === 403) {
      return serverMessage || "Access restricted. Please contact the administrator.";
    }
    if (status === 404) {
      return "Authentication service unavailable. Please try again later.";
    }
    if (status >= 500) {
      return "Server temporarily unavailable. Please try again in a moment.";
    }
    return serverMessage || "Authentication failed. Please try again.";
  }
  if (err?.request) {
    return "Cannot reach the server. Please check your connection.";
  }
  return "Something went wrong. Please try again.";
}

/** Notification styling that matches the main Fusion client's toasts. */
export const NOTIFICATION_STYLES = Object.freeze({
  success: {
    root: {
      background: "linear-gradient(135deg, #10B981 0%, #059669 100%)",
      border: "none",
      borderRadius: 8,
      boxShadow: "0 8px 24px rgba(16, 185, 129, 0.25)",
    },
    title: { color: "#fff", fontWeight: 800, letterSpacing: 1, fontSize: 13 },
    description: { color: "rgba(255,255,255,0.95)" },
  },
  error: {
    root: {
      background: "linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)",
      border: "none",
      borderRadius: 8,
      boxShadow: "0 8px 24px rgba(255, 107, 53, 0.25)",
    },
    title: { color: "#fff", fontWeight: 800, letterSpacing: 1, fontSize: 13 },
    description: { color: "rgba(255,255,255,0.95)" },
    closeButton: { color: "#fff" },
  },
});
