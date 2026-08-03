import { createContext, useContext, useEffect, useMemo } from "react";
import { Alert, Center, Loader, Text } from "@mantine/core";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import {
  setRecruiterCsrfToken, setRecruiterUnauthorizedHandler, useRecruiterLogout,
  useRecruiterSession, type RecruiterSession,
} from "./api";

interface Value {
  session: RecruiterSession | null;
  status: "loading" | "authenticated" | "anonymous" | "unavailable";
  logout: () => void;
}

const Ctx = createContext<Value | null>(null);

/** Auth for the recruiter portal. Deliberately separate from the institute
 *  AuthProvider: different credential, different login page, different 401
 *  destination. Sharing one context is how a signed-out recruiter ends up on
 *  the institute login screen. */
export function RecruiterAuthProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { data, isPending, isError } = useRecruiterSession();
  const logoutMutation = useRecruiterLogout();

  // Re-armed on every /me, so a refreshed tab can write again.
  useEffect(() => {
    setRecruiterCsrfToken(data?.csrf_token ?? "");
  }, [data?.csrf_token]);

  useEffect(() => {
    setRecruiterUnauthorizedHandler(() => navigate("/recruiter/login",
      { replace: true }));
    return () => setRecruiterUnauthorizedHandler(() => {});
  }, [navigate]);

  const value = useMemo<Value>(() => {
    const session = data ?? null;
    return {
      session,
      status: isPending ? "loading"
        : isError ? "unavailable"
        : session ? "authenticated" : "anonymous",
      logout: () => logoutMutation.mutate(undefined, {
        onSettled: () => navigate("/recruiter/login", { replace: true }),
      }),
    };
  }, [data, isPending, isError, logoutMutation, navigate]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useRecruiterAuth(): Value {
  const v = useContext(Ctx);
  if (!v) throw new Error("useRecruiterAuth must be used inside the provider");
  return v;
}

export function RequireRecruiter({ children }: { children: React.ReactNode }) {
  const { status } = useRecruiterAuth();
  const location = useLocation();

  if (status === "loading") {
    return <Center h="100vh"><Loader /></Center>;
  }
  // Not a logout: signing in again cannot work while the server is unreachable.
  if (status === "unavailable") {
    return (
      <Center h="100vh" p="md">
        <Alert color="red" title="Cannot verify your session" maw={460}>
          <Text size="sm">
            The portal could not be reached, so it is not known whether you are
            signed in. You have not been signed out — reload once it is back.
          </Text>
        </Alert>
      </Center>
    );
  }
  if (status === "anonymous") {
    return <Navigate to="/recruiter/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
