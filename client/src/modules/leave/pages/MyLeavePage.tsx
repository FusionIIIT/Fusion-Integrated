import { useState } from "react";
import { Button, Card, Container, Group, SimpleGrid, Text } from "@mantine/core";
import { FaCalendarPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances, useMyRequests } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { ActionModal, type PendingAction } from "../components/ActionModal";
import { ApplyLeaveModal } from "../components/ApplyLeaveModal";
import { LeaveStatusBadge, period } from "../components/LeaveStatusBadge";

const PENDING = new Set(["awaiting_substitute", "applicant_action_required",
  "awaiting_unit_head", "awaiting_establishment", "awaiting_final_decision"]);
const CONTINUOUS = new Set(["EL", "COL", "VL"]);

/** Which actions a row offers; the server re-checks every one of them. */
function actionsFor(r: LeaveRequest, today: string): PendingAction[] {
  const out: PendingAction[] = [];
  if (PENDING.has(r.status) && r.kind !== "cancellation") {
    out.push({ id: r.id, action: "withdraw", title: "Withdraw this request", danger: true });
  }
  if (r.status === "applicant_action_required") {
    out.push({ id: r.id, action: "renominate", title: "Nominate another substitute",
      numberField: "substitute_user_id" });
  }
  const own = r.kind === "new" && r.status === "approved" && r.source === "online";
  if (own && today < r.start_date) {
    out.push({ id: r.id, action: "cancel", title: "Request cancellation", danger: true });
  }
  if (own && CONTINUOUS.has(r.category) && today >= r.start_date) {
    out.push({ id: r.id, action: "extend", title: "Request extension",
      dateField: "new_end_date", textField: "purpose" });
    if (!r.resumption_status) {
      out.push({ id: r.id, action: "resumption", title: "Submit resumption of duty",
        dateField: "actual_date", textField: "remarks" });
    }
  }
  return out;
}

export default function MyLeavePage() {
  const { can } = useAuth();
  const year = new Date().getFullYear();
  const balances = useBalances(year);
  const mine = useMyRequests();
  const [applying, setApplying] = useState(false);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const today = new Date().toISOString().slice(0, 10);

  if (balances.error || mine.error) {
    return <Container size="xl"><ErrorState error={balances.error ?? mine.error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leave" subtitle={`Balances and requests for ${year}`}
        action={can("leave_management.leave_request.create") && (
          <Button leftSection={<FaCalendarPlus />} onClick={() => setApplying(true)}>
            Apply for leave
          </Button>)} />

      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} mb="lg">
        {(balances.data?.results ?? []).map((b) => (
          <Card key={b.category} padding="md" withBorder>
            <Text size="xs" c="dimmed">{b.label}</Text>
            <Text fw={700} size="xl">{Number(b.available)}</Text>
            <Text size="xs" c="dimmed">
              {Number(b.balance)} balance · {Number(b.held)} pending
            </Text>
          </Card>
        ))}
      </SimpleGrid>

      <DataTable<LeaveRequest>
        rows={mine.data?.results ?? []} loading={mine.isPending} rowKey={(r) => r.id}
        empty={{ title: "No leave requests yet",
          description: "Requests you submit will appear here with their status." }}
        columns={[
          { key: "id", header: "#", render: (r) => `#${r.id}` },
          { key: "kind", header: "Type",
            render: (r) => (r.kind === "new" ? r.category : `${r.category} ${r.kind}`) },
          { key: "period", header: "Period", render: period },
          { key: "days", header: "Days", align: "right", render: (r) => Number(r.days) },
          { key: "status", header: "Status",
            render: (r) => <LeaveStatusBadge status={r.status} /> },
          { key: "actions", header: "", render: (r) => (
            <Group gap={4} wrap="nowrap">
              {actionsFor(r, today).map((a) => (
                <Button key={a.action} size="compact-xs" variant="light"
                  color={a.danger ? "red" : "blue"} onClick={() => setPending(a)}>
                  {a.title.split(" ")[0]}
                </Button>
              ))}
              {can("leave_management.leave_request.export") && (
                <Button size="compact-xs" variant="subtle" component="a" target="_blank"
                  href={`/api/v1/leave/requests/${r.id}/print`}>Print</Button>
              )}
            </Group>) },
        ]}
      />
      <ApplyLeaveModal opened={applying} onClose={() => setApplying(false)} />
      <ActionModal pending={pending} onClose={() => setPending(null)} />
    </Container>
  );
}
