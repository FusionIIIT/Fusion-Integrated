import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes, usePendingApprovals, useDecide } from "../api";
import type { LeaveApplication } from "../api";

export default function LeaveApprovalsPage() {
  const { data: applications, isPending, error } = usePendingApprovals();
  const types = useLeaveTypes();
  const decide = useDecide();

  const act = (r: LeaveApplication, approve: boolean) => {
    decide.mutate({ id: r.id, approve, remarks: "" }, {
      onSuccess: () => notifications.show({
        color: approve ? "green" : "gray",
        title: approve ? "Approved" : "Rejected",
        message: `Application #${r.id}`
      }),
      onError: (e: unknown) => notifications.show({
        color: "red",
        title: "Could not save decision",
        message: errorMessage(e)
      })
    });
  };

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Approvals" subtitle="Pending applications waiting for your decision" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={applications ?? []}
          loading={isPending}
          rowKey={r => r.id}
          columns={[
            { key: "employee_id", header: "Employee" },
            { key: "leave_type", header: "Leave type", render: r => types.data?.find(t => t.id === r.leave_type)?.name },
            { key: "start_date", header: "From" },
            { key: "end_date", header: "To" },
            { key: "days", header: "Days" },
            { key: "reason", header: "Reason" },
            {
              key: "actions",
              header: "",
              align: "right",
              render: r => (
                <Group justify="flex-end" gap="xs">
                  <Button
                    size="xs"
                    color="green"
                    onClick={() => act(r, true)}
                    loading={decide.isPending}
                  >
                    Approve
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="light"
                    onClick={() => act(r, false)}
                    loading={decide.isPending}
                  >
                    Reject
                  </Button>
                </Group>
              )
            }
          ]}
          empty={{ title: "Nothing to review", description: "Pending leave applications will appear here." }}
        />
      </Card>
    </Container>
  );
}
