import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { errorMessage, http, setCsrfToken } from "../lib/http";
import AuthScreen from "../pages/Login/AuthScreen";
import { CONFIG, SURFACE_TAG } from "../pages/Login/constants";

/**
 * The single user login — students, faculty and staff, all modules.
 *
 * This is NOT the Fusion_System_Administrator console login. Operators sign in
 * separately at /sysadmin/ against their own account pool. Two audiences, two
 * doors, one identity service behind both — and, because the composition is
 * shared, two doors that look like the same building.
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [shake, setShake] = useState(false);

  async function submit({ username, password }: {
    username: string; password: string;
  }) {
    if (busy) return;                       // double-submit guard
    setBusy(true);
    setError(null);
    try {
      const { data } = await http.post<{ csrf_token: string }>(
        "/auth/login", { username, password });
      // Armed before /me runs, so the first write need not wait for it.
      setCsrfToken(data.csrf_token);
      await qc.invalidateQueries({ queryKey: ["session"] });
      navigate(CONFIG.POST_LOGIN_ROUTE, { replace: true });
    } catch (err) {
      // Deliberately does not distinguish "no such user" from "wrong password".
      setError(errorMessage(err));
      setShake(true);
      setTimeout(() => setShake(false), CONFIG.SHAKE_DURATION_MS);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthScreen
      tag={SURFACE_TAG}
      onSubmit={submit}
      loading={busy}
      error={error}
      onClearError={() => setError(null)}
      shake={shake}
    />
  );
}
