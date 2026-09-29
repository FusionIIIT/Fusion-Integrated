import { Container, Text, Title } from "@mantine/core";
import { Suspense } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { AppShellLayout } from "../ui/layout/AppShellLayout";

/** Fusion-client owns the sidebar, roles and header; a second set would drift. */
export function isEmbedded(): boolean {
  // Being framed is the reliable signal; an internal redirect drops the query.
  try {
    if (window.self !== window.top) return true;
  } catch {
    return true;                 // cross-origin parent; only a frame can throw
  }
  return new URLSearchParams(window.location.search).get("embed") === "1";
}

export function Shell() {
  const { session, logout, switchRole } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  if (!session) return null;

  if (isEmbedded()) {
    return (
      <Suspense fallback={null}>
        <Outlet />
      </Suspense>
    );
  }

  // The profile screen belongs to whichever module the server actually gave us.
  const profilePath = session.navigation
    .flatMap((g) => g.items)
    .flatMap((i) => i.links ?? (i.to ? [{ ...i, to: i.to }] : []))
    .find((l) => l.to?.endsWith("/profile"))?.to ?? "";

  return (
    <AppShellLayout
      // Straight from the server. No filter, no map, no client-side logic.
      navGroups={session.navigation}
      activePath={pathname}
      onNavigate={navigate}
      brandSubtitle="FUSION · INTEGRATED"
      user={{
        name: session.user.display_name || session.user.username,
        roleLabel: session.active_role ?? session.user.kind,
      }}
      onLogout={logout}
      profilePath={profilePath}
      roles={session.roles}
      role={session.active_role}
      onRoleChange={switchRole}
    >
      <Suspense fallback={null}>
        <Outlet />
      </Suspense>
    </AppShellLayout>
  );
}

export function NotFound() {
  return (
    <Container size="xl">
      <Title order={2} mt="xl">Not found</Title>
      <Text c="dimmed" mt="xs">
        This page does not exist, or the module it belongs to is not enabled for
        your role.
      </Text>
    </Container>
  );
}

export function Dashboard() {
  const { session } = useAuth();
  // Grants span every Fusion app; only local modules have an entry here.
  const granted = session?.modules.length ?? 0;
  const here = (session?.navigation ?? []).reduce((n, g) => n + g.items.length, 0);
  return (
    <Container size="xl">
      <Title order={2} mt="sm">
        Welcome, {session?.user.display_name || session?.user.username}
      </Title>
      <Text c="dimmed" mt="xs">
        {here
          ? `${here} of your ${granted} module(s) live here. Pick one from the sidebar.`
          : granted
            ? `Your ${granted} granted module(s) are served by another Fusion app.`
            : "No modules have been granted to your role yet."}
      </Text>
    </Container>
  );
}
