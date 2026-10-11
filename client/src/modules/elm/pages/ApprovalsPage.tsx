import { useState } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovals, useTransition } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

/** Pending requests in scope. Never your own — the server refuses that row. */
export default function ApprovalsPage() {
  const { data, isPending, error } = useApprovals();
  const transition = useTransition();
  const [decision, setDecision] = useState<{
    application: LeaveApplication; to: "approved" | "rejected";
  } | null>(null);
  const [note, setNote] = useState("");

  if (error) {
    return <Container size="xl"><ErrorState error={error} /></Container>;
  }

  function confirm() {
    if (!decision) return;
    transition.mutate(
      { id: decision.application.id, to_status: decision.to, note },
      {
        onSuccess: () => {
          notifications.show({
            color: decision.to === "approved" ? "green" : "gray",
            title: decision.to === "approved" ? "Approved" : "Rejected",
            message: `Leave for ${decision.application.applicant_name || `user ${decision.application.user_id}`}`
              + ` is now ${decision.to}.`,
          });
          setDecision(null); setNote("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not decide", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Approvals"
        subtitle="Pending leave requests awaiting a decision"
      />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={(data?.results ?? []) as LeaveApplication[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            title: "Nothing to decide",
            description: "Pending requests appear here for approval.",
          }}
          columns={[
            {
              key: "applicant", header: "Applicant",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.applicant_name || `User ${r.user_id}`}</Text>
                  <Text size="xs" c="dimmed">#{r.user_id}</Text>
                </Stack>
              ),
            },
            {
              key: "type", header: "Type",
              render: (r) => `${r.leave_type.code} — ${r.leave_type.name}`,
            },
            {
              key: "dates", header: "Dates",
              render: (r) => (
                <Text size="sm">{r.start_date} → {r.end_date}</Text>
              ),
            },
            { key: "days", header: "Days", render: (r) => r.days },
            {
              key: "reason", header: "Reason",
              render: (r) => <Text size="sm" c="dimmed">{r.reason || "—"}</Text>,
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <Button size="xs" color="green" variant="light"
                          onClick={() => { setDecision({ application: r, to: "approved" }); setNote(""); }}>
                    Approve
                  </Button>
                  <Button size="xs" color="red" variant="light"
                          onClick={() => { setDecision({ application: r, to: "rejected" }); setNote(""); }}>
                    Reject
                  </Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={decision !== null}
        onClose={() => setDecision(null)}
        title={decision?.to === "approved" ? "Approve this request" : "Reject this request"}
      >
        <Stack>
          <Text size="sm">
            {decision?.application.leave_type.name} · {decision?.application.start_date} →{" "}
            {decision?.application.end_date} ({decision?.application.days} day(s))
          </Text>
          <Textarea
            label={decision?.to === "rejected" ? "Reason (required)" : "Note"}
            value={note} onChange={(e) => setNote(e.currentTarget.value)}
            minRows={2}
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setDecision(null)}>Cancel</Button>
            <Button
              color={decision?.to === "approved" ? "green" : "red"}
              loading={transition.isPending}
              disabled={decision?.to === "rejected" && !note.trim()}
              onClick={confirm}
            >
              {decision?.to === "approved" ? "Approve" : "Reject"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
