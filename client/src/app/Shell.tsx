import { Container, Text, Title } from "@mantine/core";
import { Suspense } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { AppShellLayout } from "../ui/layout/AppShellLayout";

export function Shell() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  if (!session) return null;

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
  return (
    <Container size="xl">
      <Title order={2} mt="sm">
        Welcome, {session?.user.display_name || session?.user.username}
      </Title>
      <Text c="dimmed" mt="xs">
        {session?.modules.length
          ? `You have access to ${session.modules.length} module(s). Pick one from the sidebar.`
          : "No modules have been granted to your role yet."}
      </Text>
    </Container>
  );
}
