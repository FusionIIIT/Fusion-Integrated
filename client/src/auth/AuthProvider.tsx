import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { errorStatus, http, setCsrfToken, setUnauthorizedHandler } from "../lib/http";
import type { Session } from "./types";

interface AuthValue {
  session: Session | null;
  /** `unavailable` is "we could not ask", which is not the same as signed out. */
  status: "loading" | "authenticated" | "anonymous" | "unavailable";
  can: (permission: string) => boolean;
  switchRole: (role: string) => void;
  hasModule: (code: string) => boolean;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isPending, isError } = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      try {
        return (await http.get<Session>("/me")).data;
      } catch (e) {
        // 401 is the answer "nobody"; anything else is a real failure.
        if (errorStatus(e) === 401) return null;
        throw e;
      }
    },
    retry: false,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: true,
  });

  // Re-armed on every /me, so a refreshed tab can write again.
  useEffect(() => {
    setCsrfToken(data?.csrf_token ?? "");
  }, [data?.csrf_token]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      qc.setQueryData(["session"], null);
      if (!window.location.pathname.startsWith("/login")) navigate("/login");
    });
  }, [navigate, qc]);

  const switchRole = useCallback(async (role: string) => {
    if (!role) return;
    try {
      const { data } = await http.patch<Session>("/me", { active_role: role });
      qc.setQueryData(["session"], data);
      // Screens are scoped by the role that drew them, so start again at the top.
      navigate("/");
    } catch {
      /* the session query is unchanged, so the select snaps back */
      qc.invalidateQueries({ queryKey: ["session"] });
    }
  }, [navigate, qc]);

  const logout = useCallback(async () => {
    try {
      await http.post("/auth/logout");
    } catch {
      /* best effort — the cookie is cleared server-side either way */
    }
    setCsrfToken("");
    qc.setQueryData(["session"], null);
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "session" });
    navigate("/login");
  }, [navigate, qc]);

  const value = useMemo<AuthValue>(() => {
    const session = data ?? null;
    const perms = new Set(session?.permissions ?? []);
    const mods = new Set(session?.modules ?? []);
    return {
      session,
      status: isPending ? "loading"
        : isError ? "unavailable"
        : session ? "authenticated" : "anonymous",
      // UX only: every one of these has a server-side counterpart.
      can: (p) => perms.has(p),
      hasModule: (m) => mods.has(m),
      switchRole,
      logout,
    };
  }, [data, isPending, isError, logout, switchRole]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside <AuthProvider>");
  return v;
}
