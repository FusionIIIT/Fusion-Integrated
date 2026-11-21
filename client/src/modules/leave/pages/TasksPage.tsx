import { useState } from "react";
import { Button, Container, Group, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReviewResumption, useTasks } from "../api/hooks";
import type { LeaveRequest, Resumption } from "../api/types";
import { ActionModal, type PendingAction } from "../components/ActionModal";
import { LeaveStatusBadge, period } from "../components/LeaveStatusBadge";

/** The choices a task offers depend only on the step it is waiting at. */
function choices(r: LeaveRequest): PendingAction[] {
  const at = (action: string, title: string, body: Record<string, unknown>,
    danger = false): PendingAction => ({ id: r.id, action, title, body, danger });
  switch (r.status) {
    case "awaiting_substitute":
      return [at("substitute", "Accept substitute duty", { accept: true }),
        at("substitute", "Decline substitute duty", { accept: false }, true)];
    case "awaiting_unit_head":
      return r.unit_head_final
        ? [at("review", "Approve", { decision: "approve" }),
          at("review", "Reject", { decision: "reject" }, true)]
        : [at("review", "Recommended", { decision: "recommended" }),
          at("review", "Not recommended", { decision: "not_recommended" }, true)];
    case "awaiting_establishment":
      return [at("route", "Verify and route", {})];
    case "awaiting_final_decision":
      return [at("decide", "Approve", { approve: true }),
        at("decide", "Reject", { approve: false }, true)];
    default:
      return [];
  }
}

export default function TasksPage() {
  const tasks = useTasks();
  const review = useReviewResumption();
  const [pending, setPending] = useState<PendingAction | null>(null);

  if (tasks.error) return <Container size="xl"><ErrorState error={tasks.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Leave Tasks"
        subtitle="Requests and resumptions waiting for your action" />
      <DataTable<LeaveRequest>
        rows={tasks.data?.requests ?? []} loading={tasks.isPending} rowKey={(r) => r.id}
        empty={{ title: "Nothing waiting for you",
          description: "Requests assigned to you by the leave hierarchy appear here." }}
        columns={[
          { key: "applicant", header: "Applicant",
            render: (r) => r.applicant_name || `User ${r.user_id}` },
          { key: "what", header: "Request",
            render: (r) => `${r.category} ${r.kind === "new" ? "" : r.kind} · ${Number(r.days)} d` },
          { key: "period", header: "Period", render: period },
          { key: "purpose", header: "Purpose",
            render: (r) => <Text size="sm" lineClamp={2}>{r.purpose}</Text> },
          { key: "status", header: "Step",
            render: (r) => <LeaveStatusBadge status={r.status} /> },
          { key: "act", header: "", render: (r) => (
            <Group gap={4} wrap="nowrap">
              {choices(r).map((c) => (
                <Button key={c.title} size="compact-xs" variant="light"
                  color={c.danger ? "red" : "green"} onClick={() => setPending(c)}>
                  {c.title}
                </Button>))}
            </Group>) },
        ]}
      />

      <Title order={4} mt="xl" mb="sm">Resumptions to review</Title>
      <DataTable<Resumption>
        rows={tasks.data?.resumptions ?? []} loading={tasks.isPending} rowKey={(r) => r.id}
        empty={{ title: "No resumptions to review" }}
        columns={[
          { key: "who", header: "Employee",
            render: (r) => r.leave.applicant_name || `User ${r.leave.user_id}` },
          { key: "leave", header: "Leave", render: (r) => `${r.leave.category} · ${period(r.leave)}` },
          { key: "actual_date", header: "Actual resumption" },
          { key: "act", header: "", render: (r) => (
            <Button size="compact-xs" loading={review.isPending}
              onClick={() => review.mutate(r.id, {
                onError: (e) => notifications.show({ color: "red",
                  title: "Could not review", message: errorMessage(e) }) })}>
              Mark reviewed
            </Button>) },
        ]}
      />
      <ActionModal pending={pending} onClose={() => setPending(null)} />
    </Container>
  );
}
