import { Badge, Button, Card, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { useState } from "react";
import { FaCheckDouble } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecide, useQueue } from "../api/hooks";
import type { Action, QueueTask } from "../api/types";
import { ACTION_LABELS, STEP_LABELS, period } from "../components/fields";
import { RequestDrawer } from "../components/RequestDrawer";

const NEEDS_REASON = new Set<Action>(["reject", "not_recommend"]);

/** The acting role's queue; switching role in the header switches what appears here. */
export default function ApprovalsPage() {
  const { session } = useAuth();
  const { data, isPending, error } = useQueue();
  const decide = useDecide();
  const [pending, setPending] = useState<{ task: QueueTask; action: Action } | null>(null);
  const [remarks, setRemarks] = useState("");
  const [open, setOpen] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function submit() {
    if (!pending) return;
    decide.mutate({ id: pending.task.id, action: pending.action, remarks }, {
      onSuccess: (r) => {
        notifications.show({ color: "green", title: ACTION_LABELS[pending.action],
          message: `Request #${r.id} is now ${r.status_label.toLowerCase()}.` });
        setPending(null);
        setRemarks("");
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Approvals"
        subtitle={`Waiting for ${session?.active_role ?? "your role"}`} />
      <Card padding="lg">
        <DataTable<QueueTask>
          rows={data ?? []} loading={isPending} rowKey={(r) => r.id} minWidth={980}
          columns={[
            { key: "who", header: "Employee", render: (t) => (
              <Stack gap={0}><Text fw={600} size="sm">{t.applicant_name}</Text>
                <Text size="xs" c="dimmed">{t.request.applicant_department}</Text></Stack>) },
            { key: "what", header: "Request", render: (t) => (
              <Stack gap={0}>
                <Button variant="subtle" size="compact-sm" onClick={() => setOpen(t.request.id)}>
                  #{t.request.id} {t.request.category_label}</Button>
                {t.request.kind !== "new" && <Text size="xs" c="dimmed">{t.request.kind}</Text>}
              </Stack>) },
            { key: "period", header: "Period", render: (t) => (
              <Stack gap={0}><Text size="sm">{period(t.request)}</Text>
                <Text size="xs" c="dimmed">{Number(t.request.days)} day(s)
                  {t.resumption ? ` · resumed ${t.resumption.resumption_date}` : ""}</Text></Stack>) },
            { key: "step", header: "Step", render: (t) => (
              <Stack gap={2}><Text size="sm">{STEP_LABELS[t.step] ?? t.step}</Text>
                <Text size="xs" c="dimmed">since {dayjs(t.opened_at).format("DD MMM HH:mm")}</Text>
                {t.escalated_at && <Badge size="xs" color="orange">escalated</Badge>}
                {t.request.unit_head_outcome && <Text size="xs" c="dimmed">
                  Unit Head: {t.request.unit_head_outcome.replace("_", " ")}</Text>}</Stack>) },
            { key: "actions", header: "", align: "right", render: (t) => (
              <Group gap="xs" justify="flex-end">
                {t.actions.map((a) => (
                  <Button key={a} size="xs" variant={a === "approve" || a === "review" || a === "forward"
                    || a === "recommend" ? "filled" : "light"}
                    color={a === "reject" || a === "not_recommend" ? "red" : undefined}
                    onClick={() => setPending({ task: t, action: a })}>{ACTION_LABELS[a]}</Button>))}
              </Group>) },
          ]}
          empty={{ icon: FaCheckDouble, title: "Nothing is waiting for you",
            description: "Requests routed to your role appear here as soon as they arrive." }}
        />
      </Card>
      <FormModal opened={pending != null} onClose={() => setPending(null)}
        title={pending ? `${ACTION_LABELS[pending.action]} request #${pending.task.request.id}` : ""}
        subtitle={pending ? `${pending.task.applicant_name} · ${period(pending.task.request)}` : ""}
        submitLabel={pending ? ACTION_LABELS[pending.action] : "Confirm"}
        danger={pending ? NEEDS_REASON.has(pending.action) : false}
        submitting={decide.isPending} error={decide.error}
        disabled={pending ? NEEDS_REASON.has(pending.action) && !remarks.trim() : false}
        disabledReason="The employee will read the reason." onSubmit={submit}>
        <Textarea label="Remarks" value={remarks} autosize minRows={2}
          required={pending ? NEEDS_REASON.has(pending.action) : false}
          onChange={(e) => setRemarks(e.currentTarget.value)} />
      </FormModal>
      <RequestDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}
