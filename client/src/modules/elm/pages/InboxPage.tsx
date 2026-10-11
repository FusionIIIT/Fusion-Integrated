import { Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInbox } from "react-icons/fa";
import { errorMessage } from "../../../lib/http";
import { useDecide, useInbox } from "../api/hooks";
import { CATEGORY_LABELS, type LeaveApplication } from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function InboxPage() {
  const { data, isPending, error } = useInbox();
  const decide = useDecide();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function onDecide(app: LeaveApplication, approve: boolean) {
    decide.mutate(
      { id: app.id, approve },
      {
        onSuccess: () => notifications.show(
          { color: "green", title: approve ? "Approved" : "Rejected",
            message: "" }),
        onError: (e) => notifications.show(
          { color: "red", title: "Could not decide", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Inbox"
        subtitle="Requests awaiting your decision"
      />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "user", header: "Employee",
              render: (r) => <Text fw={600}>#{r.user_id}</Text> },
            { key: "category", header: "Type",
              render: (r) => CATEGORY_LABELS[r.category] },
            { key: "period", header: "Period",
              render: (r) => `${r.start_date} — ${r.end_date}` },
            { key: "days", header: "Days", render: (r) => r.chargeable_days },
            { key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <Button size="xs" color="green" loading={decide.isPending}
                          onClick={() => onDecide(r, true)}>Approve</Button>
                  <Button size="xs" color="red" variant="light"
                          loading={decide.isPending}
                          onClick={() => onDecide(r, false)}>Reject</Button>
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaInbox,
            title: "Inbox is empty",
            description: "No requests are waiting for a decision.",
          }}
        />
      </Card>
    </Container>
  );
}
