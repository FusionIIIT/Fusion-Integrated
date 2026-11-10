import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthProvider";
import { errorMessage } from "../../lib/http";
import { get, type Row } from "./api";

/** AFR-IAA-067: role-scoped notifications are visible from Fusion's dashboard. */
export default function DashboardWidget() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const assigned = useQuery({ queryKey: ["iaa-session", session?.user.id],
    queryFn: () => get<{ roles: { role: string }[] }>("session", "") });
  const roles = [...new Set(assigned.data?.roles.map(r => r.role) ?? [])];
  const selected = sessionStorage.getItem(`iaa-role:${session?.user.id}`) ?? "";
  const role = roles.includes(selected) ? selected : roles.length === 1 ? roles[0] ?? "" : "";
  const messages = useQuery({ queryKey: ["iaa", role, "dashboard-notifications"],
    enabled: !!role && role !== "System Admin", queryFn: () =>
      get<{ results: Row[] }>("notifications", role) });
  return <Paper withBorder p="lg" mt="xl"><Stack gap="sm">
    <Group justify="space-between"><Title order={3}>Institute Accounts and Audits</Title>
      <Button variant="light" onClick={() => navigate("/iaa/workspace?tab=notifications")}>Open IAA</Button></Group>
    {(assigned.error || messages.error) && <Alert color="red">{errorMessage(assigned.error ?? messages.error)}</Alert>}
    {!role && !assigned.error && <Text c="dimmed">Open IAA to select an assigned role and view your notifications.</Text>}
    {role === "System Admin" && <Text c="dimmed">Your active IAA role provides configuration access.</Text>}
    {role && role !== "System Admin" && <Text size="sm" c="dimmed">Latest notifications · {role}</Text>}
    {messages.isFetching && <Text size="sm">Loading notifications…</Text>}
    {messages.data?.results.slice(0, 5).map(row => <Text key={row.id} size="sm">{String(row.message)}</Text>)}
    {messages.data && !messages.data.results.length && <Text c="dimmed">No notifications for this role.</Text>}
  </Stack></Paper>;
}
