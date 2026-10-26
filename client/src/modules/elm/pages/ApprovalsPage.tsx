import { Alert, Card, Container, Text } from "@mantine/core";
import { FaClipboardCheck, FaInfoCircle } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveApprovals } from "../api";
import type { LeaveApproval } from "../types";

export default function ApprovalsPage() {
  const { data, isPending, error } = useLeaveApprovals();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const approvals = (data ?? []) as LeaveApproval[];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approvals"
        subtitle="Review leave applications submitted for your approval or recommendation"
      />
      <Alert
        icon={<FaInfoCircle size={16} />}
        title="Approval Workflow Note"
        color="blue"
        mb="md"
        variant="light"
      >
        Approval decision updates are not currently supported by backend endpoints.
        Applications assigned to you are listed below for inspection.
      </Alert>
      <Card padding="lg" withBorder>
        <DataTable<LeaveApproval>
          rows={approvals}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            {
              key: "application",
              header: "Application ID",
              render: (r) => (
                <Text fw={600}>Application #{r.leave_application}</Text>
              ),
            },
            {
              key: "stage",
              header: "Stage",
              render: (r) => `Stage ${r.stage}`,
            },
            {
              key: "decision",
              header: "Decision",
              render: (r) => <StatusBadge status={r.decision} />,
            },
            {
              key: "comments",
              header: "Comments",
              render: (r) => r.comments || "—",
            },
            {
              key: "decided_at",
              header: "Decided At",
              render: (r) =>
                r.decided_at ? new Date(r.decided_at).toLocaleString() : "Pending",
            },
            {
              key: "created_at",
              header: "Assigned Date",
              render: (r) =>
                r.created_at ? new Date(r.created_at).toLocaleDateString() : "—",
            },
          ]}
          empty={{
            icon: FaClipboardCheck,
            title: "No pending approvals",
            description: "You have no leave applications awaiting your approval.",
          }}
        />
      </Card>
    </Container>
  );
}
