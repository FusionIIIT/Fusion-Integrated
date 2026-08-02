import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { http, setCsrfToken, setUnauthorizedHandler } from "../lib/http";
import type { Session } from "./types";

interface AuthValue {
  session: Session | null;
  status: "loading" | "authenticated" | "anonymous";
  can: (permission: string) => boolean;
  hasModule: (code: string) => boolean;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isPending, isError } = useQuery({
    queryKey: ["session"],
    queryFn: async () => (await http.get<Session>("/me")).data,
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

  const logout = useCallback(async () => {
    try {
      await http.post("/auth/logout");
    } catch {
      /* best effort — the cookie is cleared server-side either way */
    }
    setCsrfToken("");
    qc.clear();
    navigate("/login");
  }, [navigate, qc]);

  const value = useMemo<AuthValue>(() => {
    const session = (isError ? null : data) ?? null;
    const perms = new Set(session?.permissions ?? []);
    const mods = new Set(session?.modules ?? []);
    return {
      session,
      status: isPending ? "loading" : session ? "authenticated" : "anonymous",
      // UX only. Every one of these has a server-side counterpart; hiding a
      // button is not an authorization control.
      can: (p) => perms.has(p),
      hasModule: (m) => mods.has(m),
      logout,
    };
  }, [data, isPending, isError, logout]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside <AuthProvider>");
  return v;
}
