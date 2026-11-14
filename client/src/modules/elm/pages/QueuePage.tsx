import { Button, Card, Container, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecide, useQueue } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { LeaveTable } from "../components/LeaveTable";
import { NoteModal } from "../components/NoteModal";

const LABEL: Record<string, string> = {
  approve: "Approve", reject: "Reject", recommend: "Recommend",
  not_recommend: "Not recommended", forward: "Forward",
  cancel_advance: "Forward cancellation", cancel_approve: "Approve cancellation",
  cancel_reject: "Reject cancellation",
};
const NEEDS_REASON = new Set(["reject", "not_recommend", "cancel_reject"]);

export default function QueuePage() {
  const { data, isPending, error } = useQueue();
  const decide = useDecide();
  const [pick, setPick] = useState<{ row: LeaveRequest; event: string } | null>(null);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Leave Approvals"
        subtitle="Requests waiting at the step held by the role you are acting as" />
      <Card withBorder padding="md">
        <LeaveTable rows={data?.results ?? []} loading={isPending} showApplicant
          empty={{ title: "Nothing awaits you",
            description: "Requests routed to your role appear here." }}
          actions={(r) => r.allowed_decisions.map((e) => (
            <Button key={e} size="xs"
              variant={NEEDS_REASON.has(e) ? "light" : "filled"}
              color={NEEDS_REASON.has(e) ? "red" : undefined}
              onClick={() => setPick({ row: r, event: e })}>{LABEL[e] ?? e}</Button>
          ))} />
      </Card>
      <NoteModal
        opened={pick != null} title={pick ? `${LABEL[pick.event] ?? pick.event} leave #${pick.row.id}` : ""}
        subtitle={pick ? `${pick.row.applicant_name} · ${pick.row.category_label} · ${pick.row.start_date} to ${pick.row.end_date}` : ""}
        label={pick && NEEDS_REASON.has(pick.event) ? "Reason" : "Note (optional)"}
        required={pick ? NEEDS_REASON.has(pick.event) : false}
        submitLabel={pick ? (LABEL[pick.event] ?? pick.event) : ""} danger={pick ? NEEDS_REASON.has(pick.event) : false}
        submitting={decide.isPending} onClose={() => setPick(null)}
        onSubmit={(note) => pick && decide.mutate({ id: pick.row.id, event: pick.event, note }, {
          onSuccess: () => setPick(null),
          onError: (e) => notifications.show({ color: "red", title: "Not recorded",
            message: errorMessage(e) }),
        })}
      >
        {pick && (
          <Stack gap={4} mb="sm">
            <Text size="sm"><b>Purpose:</b> {pick.row.purpose}</Text>
            {pick.row.recommendation && (
              <Text size="sm"><b>Unit Head:</b> {pick.row.recommendation.replace("_", " ")}</Text>)}
            {pick.row.station_leave && (
              <Text size="sm"><b>Station leave:</b> {pick.row.station_address}</Text>)}
          </Stack>
        )}
      </NoteModal>
    </Container>
  );
}
