import { useState } from "react";
import { Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../lib/http";
import AuthScreen from "../pages/Login/AuthScreen";
import { CONFIG, RECRUITER_SURFACE_TAG } from "../pages/Login/constants";
import { BRAND } from "../ui/theme/theme";
import { useRecruiterLogin } from "./api";

/**
 * The recruiter portal login: the same composition as the institute door, told
 * apart by the header tag and a footer note pointing institute users
 * elsewhere.
 */
export default function RecruiterLoginPage() {
  const navigate = useNavigate();
  const login = useRecruiterLogin();
  const [error, setError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);

  function submit({ username, password }: {
    username: string; password: string;
  }) {
    if (login.isPending) return;
    setError(null);
    login.mutate({ email: username, password }, {
      onSuccess: () => navigate("/recruiter/postings", { replace: true }),
      // Does not distinguish "no such account" from "wrong password".
      onError: (err) => {
        setError(errorMessage(err));
        setShake(true);
        setTimeout(() => setShake(false), CONFIG.SHAKE_DURATION_MS);
      },
    });
  }

  return (
    <AuthScreen
      tag={RECRUITER_SURFACE_TAG}
      heading="Recruiter Login"
      identifierLabel="WORK EMAIL"
      identifierPlaceholder="you@company.com"
      identifierType="email"
      onSubmit={submit}
      loading={login.isPending}
      error={error}
      onClearError={() => setError(null)}
      shake={shake}
      footer={
        <>
          <Text size="xs" c="dimmed" mt="xs">
            Recruiter access is by invitation from the placement office — there
            is no self-registration.
          </Text>
          <Text size="xs" c="dimmed">
            Students and staff sign in at{" "}
            <Text component="a" href="/login" size="xs" c={BRAND.primary}>
              the main portal
            </Text>.
          </Text>
        </>
      }
    />
  );
}
