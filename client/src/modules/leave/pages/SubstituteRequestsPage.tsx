import { Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CATEGORY_LABELS, useInbox, useSubstituteResponse, type LeaveApplication } from "../api";

export default function SubstituteRequestsPage() {
  const respondMutation = useSubstituteResponse();
  const inboxData = useInbox();

  if (inboxData.isPending) {
    return (
      <Container size="xl">
        <PageHeader title="Substitute Requests" subtitle="Manage substitute requests" />
        <Card padding="lg">
          <Text>Processing...</Text>
        </Card>
      </Container>
    );
  }

  if (inboxData.error) {
    return (
      <Container size="xl">
        <PageHeader title="Substitute Requests" subtitle="Colleagues who nominated you as their substitute" />
        <ErrorState error={inboxData.error} />
      </Container>
    );
  }

  const applications = (inboxData.data ?? []).filter((app) => app.stage === "substitute");

  if (applications.length === 0) {
    return (
      <Container size="xl">
        <PageHeader title="Substitute Requests" subtitle="Requests addressed to you" />
        <Card padding="lg">
          <Text>No substitute requests</Text>
        </Card>
      </Container>
    );
  }

  const columns: Column<LeaveApplication>[] = [
    { key: "colleague", header: "Colleague", align: "left", render: (row) => row.user_id },
    { key: "category", header: "Category", align: "left", render: (row) => CATEGORY_LABELS[row.category] },
    { key: "dates", header: "Dates", align: "left", render: (row) => `${row.start_date} to ${row.end_date}` },
    { key: "days", header: "Days", align: "right", render: (row) => row.days },
    { key: "purpose", header: "Purpose", align: "left", render: (row) => row.purpose },
    { key: "actions", header: "Actions", align: "left", render: (row) => (
      <Group>
        <Button size="xs" leftSection={<FaCheck size={14} />} onClick={() => handleAccept(row.id)}>
          Accept
        </Button>
        <Button size="xs" leftSection={<FaTimes size={14} />} color="red" onClick={() => handleDecline(row.id)}>
          Decline
        </Button>
      </Group>
    )},
  ];

  function handleAccept(id: number) {
    respondMutation.mutate({ id, accept: true }, {
      onSuccess: () => notifications.show({ color: "green", title: "Accepted", message: "The request now goes to the approver." }),
      onError: (e) => notifications.show({ color: "red", title: "Error", message: errorMessage(e) }),
    });
  }

  function handleDecline(id: number) {
    respondMutation.mutate({ id, accept: false }, {
      onSuccess: () => notifications.show({ color: "gray", title: "Declined", message: "Your colleague will nominate someone else." }),
      onError: (e) => notifications.show({ color: "red", title: "Error", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Substitute Requests" subtitle="Requests addressed to you" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={applications}
          columns={columns}
          loading={inboxData.isPending}
          rowKey={(row: LeaveApplication) => row.id}
          empty={{ title: "No substitute requests", description: "You have no active substitute requests." }}
        />
      </Card>
    </Container>
  );
}
