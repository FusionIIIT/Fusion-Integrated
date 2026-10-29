import { useState } from "react";
import {
  Alert, Badge, Button, Container, Group, Modal, Radio, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaGavel } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovals, useDecideTask } from "../api/hooks";
import type { ApprovalTask } from "../api/types";

/** Which steps are recommendations and which are decisions.
 *
 *  BR-EL-017: on higher-sanction leave the Unit Head records a recommendation,
 *  and `not_recommended` is not a refusal — the request still goes up. On CL and
 *  RH the Unit Head decides outright. Offering the wrong control here is how a
 *  Unit Head unknowingly rejects leave. */
const UNIT_HEAD_STEPS = new Set([
  "unit_head_decision", "cancellation_unit_head", "extension_unit_head",
]);
const UNIT_HEAD_FINAL_STEPS = new Set(["unit_head_decision"]);

/** BR-EL-029 aside, these are the two shapes of authority step. */
const FINAL_KINDS = new Set([
  "final_sanction", "director_self_sanction", "cancellation_final",
  "extension_final",
]);

export default function ApprovalsPage() {
  const tasks = useApprovals();
  const decide = useDecideTask(0);
  const [acting, setActing] = useState<{ task: ApprovalTask; approve: boolean } | null>(
    null);
  const [note, setNote] = useState("");
  const [recommendation, setRecommendation] = useState<string | null>("recommended");

  if (tasks.isError) {
    return <Container size="xl"><ErrorState error={tasks.error} /></Container>;
  }

  const rows = tasks.data ?? [];

  function open(task: ApprovalTask, approve: boolean) {
    setActing({ task, approve });
    setNote("");
    setRecommendation("recommended");
  }

  function send() {
    if (!acting) return;
    const isRecommendationOnly = UNIT_HEAD_STEPS.has(acting.task.kind)
      && !FINAL_KINDS.has(acting.task.kind);
    decide.mutate({
      id: acting.task.id,
      approve: acting.approve,
      note: note.trim(),
      recommendation: isRecommendationOnly
        ? (recommendation ?? "recommended")
        : "",
    }, {
      onSuccess: () => {
        notifications.show({
          color: acting.approve ? "green" : "gray",
          title: acting.approve ? "Approved" : "Rejected",
          message: `Request #${acting.task.leave_request_id} has been decided.`,
        });
        setActing(null);
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not record the decision",
        message: errorMessage(e),
      }),
    });
  }

  const columns: Column<ApprovalTask>[] = [
    { key: "request", header: "Request",
      render: (t) => <Text size="sm">#{t.leave_request_id}</Text> },
    { key: "workflow", header: "Workflow",
      render: (t) => (
        <Stack gap={2}>
          <Badge size="sm" variant="light">{t.subject_type}</Badge>
          <Text size="xs" c="dimmed">{t.kind.replace(/_/g, " ")}</Text>
        </Stack>
      ) },
    { key: "waiting", header: "Waiting since",
      render: (t) => <Text size="sm">{t.assigned_at?.slice(0, 16).replace("T", " ")}</Text> },
    { key: "sla", header: "SLA",
      render: (t) => (t.escalated_at
        ? <Badge color="red" variant="light" size="sm">Escalated</Badge>
        : t.reminder_sent_at
          ? <Badge color="yellow" variant="light" size="sm">Reminded</Badge>
          : <Text size="xs" c="dimmed">—</Text>) },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (t) => (
        <Group gap="xs" justify="flex-end" wrap="nowrap">
          <Button size="compact-xs" onClick={() => open(t, true)}>Approve</Button>
          <Button size="compact-xs" variant="light" color="red"
                  onClick={() => open(t, false)}>Reject</Button>
        </Group>
      ),
    },
  ];

  const actingIsRecommendation = acting
    && UNIT_HEAD_STEPS.has(acting.task.kind) && !FINAL_KINDS.has(acting.task.kind);

  return (
    <Container size="xl">
      <PageHeader title="Approvals" subtitle="Requests waiting on you" />
      <DataTable
        rows={rows}
        columns={columns}
        loading={tasks.isPending}
        rowKey={(t) => t.id}
        minWidth={760}
        empty={{
          icon: FaGavel,
          title: "Nothing waiting on you",
          description: "Requests appear here when routing reaches you.",
        }}
      />

      <Modal opened={!!acting} onClose={() => setActing(null)}
             title={acting?.approve ? "Approve request" : "Reject request"}
             centered>
        <Stack>
          {actingIsRecommendation && !UNIT_HEAD_FINAL_STEPS.has(acting!.task.kind) && (
            <Alert color="blue" variant="light">
              On this leave type you record a recommendation. The request still
              goes to the next authority either way.
            </Alert>
          )}
          {actingIsRecommendation && (
            <Radio.Group label="Recommendation" value={recommendation ?? ""}
                         onChange={setRecommendation}>
              <Stack mt="xs" gap="xs">
                <Radio value="recommended" label="Recommended" />
                <Radio value="not_recommended" label="Not recommended" />
              </Stack>
            </Radio.Group>
          )}
          <Text size="sm" c="dimmed">
            Task {acting?.task.kind.replace(/_/g, " ")} on request #
            {acting?.task.leave_request_id}, assigned{" "}
            {acting?.task.assigned_at?.slice(0, 16).replace("T", " ")}.
          </Text>
          <Textarea
            label="Note" autosize minRows={2} value={note}
            onChange={(e) => setNote(e.currentTarget.value)}
            placeholder="Visible to the applicant."
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActing(null)}>Cancel</Button>
            <Button onClick={send} loading={decide.isPending}
                    color={acting?.approve ? undefined : "red"}>
              {acting?.approve ? "Approve" : "Reject"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}