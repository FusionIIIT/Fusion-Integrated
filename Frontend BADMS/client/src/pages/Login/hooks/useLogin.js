import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../context/AuthContext";
import { login as loginRequest } from "../../../services/authServices";
import { CONFIG, mapAuthError, NOTIFICATION_STYLES } from "../constants";

/**
 * Encapsulates the whole login side-effect: call the API, persist the session,
 * notify, and redirect — with a guard against double submits and a shake cue on
 * failure. Components stay presentational and just call `submit()`.
 */
export function useLogin() {
  const navigate = useNavigate();
  const { login: persistSession } = useAuth();
  const [loading, setLoading] = useState(false);
  const [shake, setShake] = useState(false);
  const [error, setError] = useState(null);
  const shakeTimer = useRef(null);

  const triggerShake = useCallback(() => {
    setShake(true);
    clearTimeout(shakeTimer.current);
    shakeTimer.current = setTimeout(() => setShake(false), CONFIG.SHAKE_DURATION_MS);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const submit = useCallback(
    async ({ username, password }) => {
      if (loading) return;
      setError(null);
      setLoading(true);
      try {
        // Trim the username (whitespace is never meaningful); send the password as
        // typed so we never silently alter a credential. The server sets the auth
        // cookie; we just flip the local "logged in" hint.
        await loginRequest(username.trim(), password);
        persistSession();
        notifications.show({
          title: "ACCESS GRANTED",
          message: "Authentication successful",
          color: "green",
          autoClose: 2500,
          styles: () => NOTIFICATION_STYLES.success,
        });
        // Keep `loading` true until the redirect unmounts us — avoids a flicker of
        // the enabled button between success and navigation.
        setTimeout(
          () => navigate(CONFIG.POST_LOGIN_ROUTE, { replace: true }),
          CONFIG.AUTH_SUCCESS_DELAY_MS,
        );
      } catch (err) {
        // Surface the failure inline on the form (a notification the user can't miss),
        // plus a shake cue — no easily-missed corner toast for the error path.
        setError(mapAuthError(err));
        triggerShake();
        setLoading(false);
      }
    },
    [loading, navigate, persistSession, triggerShake],
  );

  useEffect(() => () => clearTimeout(shakeTimer.current), []);

  return { submit, loading, shake, error, clearError };
}
