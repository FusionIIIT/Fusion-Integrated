/* eslint-disable react/prop-types */
/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import axiosInstance from "./axiosInstance";

const AuthContext = createContext();

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // auto sign-out after 30 min idle
const ACTIVITY_THROTTLE_MS = 30 * 1000; // refresh the idle timer at most every 30s

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(() =>
    Boolean(localStorage.getItem("isAuthenticated")),
  );

  // The auth token lives in an httpOnly cookie (set by the API on login), so there is
  // nothing secret to store here — only a non-sensitive "is logged in" UI hint.
  const login = useCallback(() => {
    localStorage.setItem("isAuthenticated", "true");
    localStorage.setItem("sessionStart", Date.now().toString());
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    // Best-effort server-side revocation; the browser attaches the auth cookie
    // automatically (withCredentials), which also clears it on the response.
    axiosInstance.post("/logout/").catch(() => {});
    setIsAuthenticated(false);
    localStorage.clear();
  }, []);

  useEffect(() => {
    const checkSession = () => {
      const sessionStart = localStorage.getItem("sessionStart");
      if (!sessionStart) return;
      if (Date.now() - parseInt(sessionStart, 10) > SESSION_TIMEOUT_MS) logout();
    };

    // Cross-tab sign-out: if another tab clears auth, follow suit here.
    const handleStorageChange = (event) => {
      if (event.key === "isAuthenticated" && event.newValue === null) {
        setIsAuthenticated(false);
      }
    };

    // Refresh the idle timer on user activity, but throttle the write so a burst of
    // mousemove/scroll events can't hammer localStorage on every frame.
    let lastActivityWrite = 0;
    const markActivity = () => {
      if (!localStorage.getItem("isAuthenticated")) return;
      const now = Date.now();
      if (now - lastActivityWrite < ACTIVITY_THROTTLE_MS) return;
      lastActivityWrite = now;
      localStorage.setItem("sessionStart", now.toString());
    };

    const activityEvents = ["click", "keydown", "mousemove", "scroll", "touchstart"];
    const interval = setInterval(checkSession, 60_000);
    window.addEventListener("storage", handleStorageChange);
    activityEvents.forEach((e) =>
      document.addEventListener(e, markActivity, { passive: true }),
    );

    return () => {
      clearInterval(interval);
      window.removeEventListener("storage", handleStorageChange);
      activityEvents.forEach((e) => document.removeEventListener(e, markActivity));
    };
  }, [logout]);

  const value = useMemo(
    () => ({ isAuthenticated, login, logout }),
    [isAuthenticated, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
