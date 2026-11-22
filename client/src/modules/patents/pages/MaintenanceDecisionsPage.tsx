import { Alert, Button, Container, Group, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaInfoCircle, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useRenewalDecision } from "../api/hooks";
import { PatentStatusBadge } from "../components/PatentStatusBadge";

function RenewalRow({ app }: { app: { id: number; application_number: string; title: string; status: string } }) {
  const renewalMutation = useRenewalDecision(app.id);

  const handleDecision = (renew: boolean) => {
    renewalMutation.mutate(
      { renew, notes: renew ? "Renewal approved by Director." : "Abandonment decided." },
      {
        onSuccess: () => {
          notifications.show({
            color: renew ? "green" : "orange",
            title: renew ? "Renewal recorded" : "Patent abandoned",
            message: `Maintenance decision recorded for ${app.title}.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Decision failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Table.Tr>
      <Table.Td>{app.application_number || `PMS-${app.id}`}</Table.Td>
      <Table.Td fw={500}>{app.title}</Table.Td>
      <Table.Td>
        <PatentStatusBadge status={app.status} />
      </Table.Td>
      <Table.Td>
        <Group gap="xs">
          <Button
            size="xs"
            color="teal"
            leftSection={<FaCheck size={10} />}
            loading={renewalMutation.isPending}
            aria-label={`Renew patent ${app.title}`}
            onClick={() => handleDecision(true)}
          >
            Renew
          </Button>
          <Button
            size="xs"
            color="red"
            variant="light"
            leftSection={<FaTimes size={10} />}
            loading={renewalMutation.isPending}
            aria-label={`Abandon patent ${app.title}`}
            onClick={() => handleDecision(false)}
          >
            Abandon
          </Button>
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

export default function MaintenanceDecisionsPage() {
  const { data, isPending, error } = useApplications();

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  if (isPending) {
    return (
      <Container size="lg">
        <Text c="dimmed">Loading…</Text>
      </Container>
    );
  }

  const applications = (data?.results ?? []).filter((app) => app.status === "GRANTED");

  return (
    <Container size="lg">
      <PageHeader
        title="Patent Maintenance Renewals"
        subtitle="Review post-grant maintenance schedules and authorize official annuity fee payments"
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No maintenance renewals due">
          <Text size="sm">There are no granted patents currently awaiting annuity maintenance decisions.</Text>
        </Alert>
      ) : (
        <Table withTableBorder withColumnBorders striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {applications.map((app) => (
              <RenewalRow key={app.id} app={app} />
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Container>
  );
}
