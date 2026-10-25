import { useState } from "react";
import { Button, Card, Container, Group, Modal, Stack, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApproveLeave, usePendingApprovals, useRejectLeave } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function LeaveApprovalsPage() {
  const { data, isPending, error } = usePendingApprovals();
  const approve = useApproveLeave();
  const reject = useRejectLeave();

  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<LeaveRequest | null>(null);
  const [mode, setMode] = useState<"approve" | "reject">("approve");
  const [remarks, setRemarks] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function confirm() {
    if (!selected) return;
    const fn = mode === "approve" ? approve : reject;
    fn.mutate(
      { id: selected.id, remarks },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Done", message: `Request ${mode}d.` });
          setModalOpen(false);
          setSelected(null);
        },
        onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="Pending Approvals" subtitle="Leave requests awaiting your decision." />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={(data ?? []) as LeaveRequest[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            { key: "leave_type_code", header: "Type", render: (r) => r.leave_type_code },
            { key: "start_date", header: "Start", render: (r) => r.start_date },
            { key: "end_date", header: "End", render: (r) => r.end_date },
            { key: "duration_days", header: "Days", render: (r) => r.duration_days },
            { key: "reason", header: "Reason", render: (r) => r.reason },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            { key: "actions", header: "", render: (r) => (
              <Group gap="xs">
                <Button size="xs" color="green" onClick={() => { setSelected(r); setMode("approve"); setRemarks(""); setModalOpen(true); }}>Approve</Button>
                <Button size="xs" color="red" onClick={() => { setSelected(r); setMode("reject"); setRemarks(""); setModalOpen(true); }}>Reject</Button>
              </Group>
            ) },
          ]}
          empty={{ title: "No pending approvals", description: "Nothing to review right now." }}
        />
      </Card>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={`${mode === "approve" ? "Approve" : "Reject"} request #${selected?.id}`}>
        <Stack gap="md">
          <Textarea label="Remarks" value={remarks} onChange={(e) => setRemarks(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button color={mode === "approve" ? "green" : "red"} loading={approve.isPending || reject.isPending} onClick={confirm}>
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}