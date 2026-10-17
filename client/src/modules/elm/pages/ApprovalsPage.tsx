import { useState } from "react";
import { Button, Card, Container, Group, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInbox } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApprovalQueue, useLeaveTransition } from "../api/hooks";
import type { LeaveRequest, LeaveStatus } from "../api/types";
import { leaveColumns } from "./columns";

const ACTION_LABELS: Partial<Record<LeaveStatus, string>> = {
  recommended: "Recommend",
  not_recommended: "Not recommend",
  approved: "Approve",
  rejected: "Reject",
};

/** Buttons come from `allowed_transitions`, which the server computes per
 *  caller, so a Unit Head never sees "Approve" on Earned Leave. */
export default function ApprovalsPage() {
  const { data, isPending, error } = useApprovalQueue();
  const transition = useLeaveTransition();
  const { session } = useAuth();
  const [pending, setPending] = useState<{ row: LeaveRequest; to: LeaveStatus } | null>(null);
  const [remarks, setRemarks] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  // The queue is everything awaiting a decision; one's own requests are on My Leave.
  const rows = (data?.results ?? []).filter((r) => r.applicant_user_id !== session?.user.id);

  function close() {
    setPending(null);
    setRemarks("");
    transition.reset();
  }

  function confirm() {
    if (!pending) return;
    transition.mutate({ id: pending.row.id, to_status: pending.to, remarks }, {
      onSuccess: (r) => {
        notifications.show({ color: "green", title: "Done",
                             message: `Request is now ${r.status.replace(/_/g, " ")}.` });
        close();
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Approvals" subtitle="Requests waiting for your decision" />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            { key: "applicant", header: "Applicant",
              render: (r) => `#${r.applicant_user_id}` },
            ...leaveColumns,
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {r.allowed_transitions.filter((t) => ACTION_LABELS[t]).map((t) => (
                    <Button key={t} size="xs"
                            variant={t === "rejected" || t === "not_recommended"
                              ? "subtle" : "light"}
                            color={t === "rejected" ? "red" : undefined}
                            onClick={() => setPending({ row: r, to: t })}>
                      {ACTION_LABELS[t]}
                    </Button>
                  ))}
                </Group>
              ),
            },
          ]}
          empty={{ icon: FaInbox, title: "Nothing to review",
                   description: "New leave requests will appear here." }}
        />
      </Card>

      <FormModal
        opened={pending !== null} onClose={close}
        title={pending ? `${ACTION_LABELS[pending.to]} request` : ""}
        submitLabel={pending ? ACTION_LABELS[pending.to] : "Confirm"}
        danger={pending?.to === "rejected"}
        submitting={transition.isPending} error={transition.error}
        onSubmit={confirm}
      >
        <Textarea label="Remarks" autosize minRows={2} maxLength={500}
                  value={remarks} onChange={(e) => setRemarks(e.currentTarget.value)} />
      </FormModal>
    </Container>
  );
}
