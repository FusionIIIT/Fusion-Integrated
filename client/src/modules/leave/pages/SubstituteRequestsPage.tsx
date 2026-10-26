import { Badge, Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubstituteRequests, useRespondToSubstituteRequest } from "../hooks/useLeaveRequests";

export default function SubstituteRequestsPage() {
  const notify = notifications;
  const { data, isPending, refetch } = useSubstituteRequests();
  const substituteRequests = data ?? { results: [] };
  const respondToSubstitute = useRespondToSubstituteRequest();

  const handleRespond = async (id: number, accept: boolean) => {
    const reason = window.prompt("Enter reason (optional):") || "";
    try {
      await respondToSubstitute.mutateAsync({ id, body: { accept, reason } });
      notify.show({ title: "Success", message: accept ? "Accepted" : "Declined", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to respond", color: "red" });
    }
  };

  return (
    <Container size="xl">
      <PageHeader title="Substitute Requests" subtitle="Substitute nominations awaiting your response" />
      <Card padding="lg">
        <DataTable
          rows={substituteRequests.results}
          loading={isPending}
          minWidth={1000}
          rowKey={(row) => row.id}
          columns={[
            { key: "id", header: "#" },
            { key: "leave_request_category", header: "Leave Category" },
            { key: "leave_request_status", header: "Leave Status" },
            {
              key: "leave_request_start",
              header: "From",
              render: (r) => new Date(r.leave_request_start).toLocaleDateString(),
            },
            {
              key: "leave_request_end",
              header: "To",
              render: (r) => new Date(r.leave_request_end).toLocaleDateString(),
            },
            { key: "substitute_id", header: "Substitute ID" },
            { key: "nominated_by", header: "Nominated By" },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Badge
                  color={r.status === "pending" ? "orange" : r.status === "accepted" ? "green" : "red"}
                  variant="light"
                >
                  {r.status}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) =>
                r.status === "pending" ? (
                  <Group>
                    <Button size="sm" color="green" onClick={() => handleRespond(r.id, true)}>
                      Accept
                    </Button>
                    <Button size="sm" color="red" onClick={() => handleRespond(r.id, false)}>
                      Decline
                    </Button>
                  </Group>
                ) : (
                  <Text color="dimmed">Completed</Text>
                ),
            },
          ]}
          empty={{ title: "No substitute requests", description: "No pending substitute nominations." }}
        />
      </Card>
    </Container>
  );
}