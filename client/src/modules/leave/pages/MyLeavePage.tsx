import {
  Alert, Button, Card, Container, Group, SimpleGrid, Stack, Tabs, Text, Title,
} from "@mantine/core";
import dayjs from "dayjs";
import { useState } from "react";
import { FaCalendarAlt, FaClipboardList } from "react-icons/fa";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLedger, useMyRequests, useOverview } from "../api/hooks";
import type { LeaveRequest, LedgerEntry } from "../api/types";
import { LeaveStatus, period } from "../components/fields";
import { RequestDrawer } from "../components/RequestDrawer";

export default function MyLeavePage() {
  const { can } = useAuth();
  const overview = useOverview();
  const requests = useMyRequests();
  const ledger = useLedger(overview.data?.year);
  const [open, setOpen] = useState<number | null>(null);

  if (overview.error) return <Container size="xl"><ErrorState error={overview.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle={overview.data ? `Balances for ${overview.data.year} · ${
          overview.data.department || "no department on record"}` : undefined}
        action={can("leave.request.create") && (
          <Button component={Link} to="/leave/apply">Apply for leave</Button>)}
      />
      {overview.data && !overview.data.configured && (
        <Alert color="yellow" mb="md" title="Leave is not set up yet">
          The Leave Administrator has not configured the leave policy. Applications open once
          it is.
        </Alert>)}
      <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} mb="lg">
        {(overview.data?.balances ?? []).filter((b) => b.applicable).map((b) => (
          <Card key={b.category} padding="md" withBorder>
            <Text size="xs" c="dimmed">{b.label}</Text>
            <Title order={3}>{Number(b.available)}</Title>
            <Text size="xs" c="dimmed">
              {Number(b.balance)} held{Number(b.pending) ? ` · ${Number(b.pending)} pending` : ""}
            </Text>
          </Card>
        ))}
      </SimpleGrid>

      <Tabs defaultValue="requests">
        <Tabs.List>
          <Tabs.Tab value="requests">Requests</Tabs.Tab>
          <Tabs.Tab value="ledger">Leave account</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="requests" pt="md">
          {requests.error ? <ErrorState error={requests.error} /> : (
            <Card padding="lg">
              <DataTable<LeaveRequest>
                rows={requests.data ?? []} loading={requests.isPending} rowKey={(r) => r.id}
                columns={[
                  { key: "id", header: "#", render: (r) => (
                    <Button variant="subtle" size="compact-sm" onClick={() => setOpen(r.id)}>
                      #{r.id}</Button>) },
                  { key: "kind", header: "Type", render: (r) => (
                    <Stack gap={0}><Text size="sm" fw={600}>{r.category_label}</Text>
                      {r.kind !== "new" && <Text size="xs" c="dimmed">{r.kind} of #{r.parent_id}</Text>}
                    </Stack>) },
                  { key: "period", header: "Period", render: (r) => period(r) },
                  { key: "days", header: "Days", render: (r) => Number(r.days) },
                  { key: "status", header: "Status",
                    render: (r) => <LeaveStatus status={r.status} label={r.status_label} /> },
                ]}
                empty={{ icon: FaClipboardList, title: "No leave requests yet",
                  description: "Requests you submit appear here with their status." }}
              />
            </Card>)}
        </Tabs.Panel>
        <Tabs.Panel value="ledger" pt="md">
          {ledger.error ? <ErrorState error={ledger.error} /> : (
            <Card padding="lg">
              <DataTable<LedgerEntry>
                rows={ledger.data?.results ?? []} loading={ledger.isPending} rowKey={(r) => r.id}
                columns={[
                  { key: "created_at", header: "Date",
                    render: (r) => dayjs(r.created_at).format("DD MMM YYYY") },
                  { key: "category", header: "Leave" },
                  { key: "entry_label", header: "Entry" },
                  { key: "delta", header: "Days", align: "right", render: (r) => (
                    <Text c={Number(r.delta) < 0 ? "red" : "green"} size="sm">
                      {Number(r.delta) > 0 ? "+" : ""}{Number(r.delta)}</Text>) },
                  { key: "note", header: "Note" },
                ]}
                empty={{ icon: FaCalendarAlt, title: "No entries this year",
                  description: "Your annual credit appears the first time you use Leave." }}
              />
            </Card>)}
        </Tabs.Panel>
      </Tabs>
      <Group mt="md" />
      <RequestDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}
