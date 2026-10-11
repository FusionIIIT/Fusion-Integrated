import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Stack, Tabs, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckDouble, FaClipboardList } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useDecideTask, useLeaveTasks, useResumptions, useReviewResumption,
} from "../api/hooks";
import type { LeaveResumption, WorkflowTask } from "../api/types";
import { CATEGORY_LABELS } from "../api/types";

/** The Unit Head is final for CL/RH and recommends for everything else
 *  (BR-EL-016 / BR-EL-017). The buttons follow the step, not the title. */
function actionsFor(task: WorkflowTask): { action: string; label: string }[] {
  const unitHeadFinal = task.category === "cl" || task.category === "rh";
  switch (task.step_kind) {
    case "unit_head":
      return unitHeadFinal
        ? [{ action: "approve", label: "Approve" }, { action: "reject", label: "Reject" }]
        : [{ action: "recommend", label: "Recommend" },
           { action: "recommend", label: "Not recommended" }];
    case "establishment":
      return [{ action: "verify", label: "Verify & forward" }];
    case "sanction":
      return task.authority === "director" || task.task_class.includes("sanction")
        ? [{ action: "approve", label: "Approve" }, { action: "reject", label: "Reject" }]
        : [{ action: "verify", label: "Forward" }];
    default:
      return [{ action: "approve", label: "Approve" }];
  }
}

export default function ApprovalsPage() {
  const [status, setStatus] = useState("pending");
  const tasks = useLeaveTasks(status);
  const decide = useDecideTask();
  const resumptions = useResumptions();
  const review = useReviewResumption();

  const [pending, setPending] = useState<{ task: WorkflowTask; action: string } | null>(null);
  const [note, setNote] = useState("");
  const [reviewFor, setReviewFor] = useState<LeaveResumption | null>(null);
  const [reviewNote, setReviewNote] = useState("");

  if (tasks.error) {
    return <Container size="xl"><ErrorState error={tasks.error} /></Container>;
  }

  function submit() {
    if (!pending) return;
    decide.mutate(
      {
        id: pending.task.id,
        action: pending.action,
        note,
        recommendation: pending.action === "recommend"
          ? (pending.task.step_kind === "unit_head" && note.toLowerCase().startsWith("not")
            ? "not_recommended" : "recommended")
          : undefined,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Recorded",
            message: "The request moved to its next state.",
          });
          setPending(null);
          setNote("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approvals"
        subtitle="Everything routed to your office, plus resumptions awaiting review"
        action={
          <Button variant="default" size="xs"
                  onClick={() => setStatus(status === "pending" ? "completed" : "pending")}>
            Showing: {status}
          </Button>
        }
      />

      <Tabs defaultValue="tasks">
        <Tabs.List mb="md">
          <Tabs.Tab value="tasks" leftSection={<FaCheckDouble size={12} />}>
            Tasks
          </Tabs.Tab>
          <Tabs.Tab value="resumptions"
                    leftSection={<FaClipboardList size={12} />}>
            Resumptions ({resumptions.data?.results.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="tasks">
          <Card withBorder padding="lg">
            <DataTable<WorkflowTask>
              rows={tasks.data?.results ?? []}
              loading={tasks.isPending}
              rowKey={(t) => t.id}
              minWidth={960}
              columns={[
                { key: "reference", header: "Reference",
                  render: (t) => <Text size="sm">{t.reference ?? `#${t.request_id}`}</Text> },
                { key: "category", header: "Category",
                  render: (t) => CATEGORY_LABELS[t.category] ?? t.category },
                { key: "period", header: "Period",
                  render: (t) => (
                    <Text size="sm">{t.period_from} → {t.period_to} ({t.days_counted}d)</Text>
                  ) },
                { key: "step", header: "Stage",
                  render: (t) => (
                    <Stack gap={0}>
                      <Badge variant="light" size="sm">
                        {t.step_kind.replace(/_/g, " ")}
                      </Badge>
                      <Text size="xs" c="dimmed">{t.task_class}</Text>
                    </Stack>
                  ) },
                { key: "sla", header: "SLA",
                  render: (t) => (
                    <Text size="xs" c={t.escalated_at ? "red" : "dimmed"}>
                      {t.escalated_at ? "escalated" : t.reminded_at ? "reminded" : "—"}
                    </Text>
                  ) },
                { key: "status", header: "Status",
                  render: (t) => <StatusBadge status={t.status} /> },
                {
                  key: "actions", header: "", align: "right",
                  render: (t) => (
                    <Group justify="flex-end" gap={4} wrap="nowrap">
                      {t.status !== "pending" ? <Text size="xs" c="dimmed">{t.note}</Text> : null}
                      {t.status === "pending" && actionsFor(t).map((a, i) => (
                        <Button
                          key={`${a.action}-${i}`} size="compact-xs"
                          variant={a.action === "reject" ? "subtle" : "light"}
                          color={a.action === "reject" ? "red" : undefined}
                          onClick={() => { setPending({ task: t, action: a.action }); setNote(""); }}
                        >
                          {a.label}
                        </Button>
                      ))}
                    </Group>
                  ),
                },
              ]}
              empty={{
                icon: FaCheckDouble,
                title: "Nothing in your queue",
                description: "Requests routed to your office appear here.",
              }}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="resumptions">
          <Card withBorder padding="lg">
            <DataTable<LeaveResumption>
              rows={resumptions.data?.results ?? []}
              loading={resumptions.isPending}
              rowKey={(r) => r.id}
              minWidth={800}
              columns={[
                { key: "reference", header: "Reference",
                  render: (r) => r.reference ?? `#${r.request_id}` },
                { key: "category", header: "Category",
                  render: (r) => CATEGORY_LABELS[r.category] ?? r.category },
                { key: "approved", header: "Approved until", render: (r) => r.approved_to },
                { key: "actual", header: "Actual return", render: (r) => r.actual_date },
                { key: "outcome", header: "Outcome", render: (r) => r.outcome_label },
                {
                  key: "actions", header: "", align: "right",
                  render: (r) => r.outcome === "pending" ? (
                    <Button size="compact-xs" variant="light"
                            onClick={() => { setReviewFor(r); setReviewNote(""); }}>
                      Review
                    </Button>
                  ) : null,
                },
              ]}
              empty={{
                icon: FaClipboardList,
                title: "No resumption submissions",
                description: "Employees returning from EL, COL or VL submit here.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      <Modal opened={pending !== null} onClose={() => setPending(null)}
             title="Record the decision">
        <Stack>
          <Text size="sm" c="dimmed">
            {pending && `${pending.task.step_kind.replace(/_/g, " ")} · ${pending.action}`}
          </Text>
          <Textarea
            label="Note" minRows={2} value={note}
            description="Required for a rejection; carried with the recommendation otherwise"
            onChange={(e) => setNote(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button loading={decide.isPending} onClick={submit}>Record</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={reviewFor !== null} onClose={() => setReviewFor(null)}
             title="Review resumption">
        <Stack>
          <Text size="sm">
            Approved until <b>{reviewFor?.approved_to}</b>, actual return{" "}
            <b>{reviewFor?.actual_date}</b>. A date that matches makes no
            adjustment; earlier or later synchronises the actual period and the
            balance.
          </Text>
          <Textarea label="Review note" minRows={2} value={reviewNote}
                    onChange={(e) => setReviewNote(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button
              loading={review.isPending}
              onClick={() => review.mutate(
                { id: reviewFor!.id, note: reviewNote }, {
                  onSuccess: () => {
                    notifications.show({
                      color: "green", title: "Reviewed",
                      message: "The actual period and balance are synchronised.",
                    });
                    setReviewFor(null);
                  },
                  onError: (e) => notifications.show({
                    color: "red", title: "Could not review", message: errorMessage(e),
                  }),
                })}
            >
              Record review
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
