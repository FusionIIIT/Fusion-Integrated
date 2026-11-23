import { Alert, Button, Container, Group, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaInfoCircle, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useBudgetDecision } from "../api/hooks";
import { PatentStatusBadge } from "../components/PatentStatusBadge";

function BudgetRow({ app }: { app: { id: number; application_number: string; title: string; status: string } }) {
  const budgetMutation = useBudgetDecision(app.id);

  const handleDecision = (decision: "APPROVE" | "REJECT") => {
    budgetMutation.mutate(
      { decision, notes: `Budget ${decision.toLowerCase()}d by Director.` },
      {
        onSuccess: () => {
          notifications.show({
            color: decision === "APPROVE" ? "green" : "red",
            title: `Budget ${decision.toLowerCase()}d`,
            message: `Budget decision recorded for ${app.title}.`,
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
            loading={budgetMutation.isPending}
            aria-label={`Approve budget for ${app.title}`}
            onClick={() => handleDecision("APPROVE")}
          >
            Approve
          </Button>
          <Button
            size="xs"
            color="red"
            variant="light"
            leftSection={<FaTimes size={10} />}
            loading={budgetMutation.isPending}
            aria-label={`Reject budget for ${app.title}`}
            onClick={() => handleDecision("REJECT")}
          >
            Reject
          </Button>
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

export default function BudgetApprovalsPage() {
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

  const applications = (data?.results ?? []).filter((app) =>
    ["BUDGET_PENDING", "APPROVED", "ATTORNEY_ASSIGNED"].includes(app.status),
  );

  return (
    <Container size="lg">
      <PageHeader
        title="Patent Budget Approvals"
        subtitle="Review and authorize filing and legal prosecution expenditure requests"
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No pending budgets">
          <Text size="sm">There are no patent expenditure requests currently awaiting authorization.</Text>
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
              <BudgetRow key={app.id} app={app} />
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Container>
  );
}
