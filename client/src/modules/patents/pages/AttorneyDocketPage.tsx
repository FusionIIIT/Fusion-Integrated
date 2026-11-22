import { Alert, Button, Container, Group, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaInfoCircle, FaPlay, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useAssessment, useRespondAssignment } from "../api/hooks";
import { PatentStatusBadge } from "../components/PatentStatusBadge";

function DocketRow({ app }: { app: { id: number; application_number: string; title: string; status: string } }) {
  const respondMutation = useRespondAssignment(app.id);
  const assessmentMutation = useAssessment(app.id);

  const handleRespond = (action: "accept" | "decline") => {
    respondMutation.mutate(action, {
      onSuccess: () => {
        notifications.show({
          color: action === "accept" ? "green" : "orange",
          title: `Assignment ${action}ed`,
          message: `Attorney assignment was ${action}ed for ${app.title}.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Response failed",
          message: errorMessage(err),
        });
      },
    });
  };

  const handleStartAssessment = () => {
    assessmentMutation.mutate("start", {
      onSuccess: () => {
        notifications.show({
          color: "blue",
          title: "Assessment started",
          message: `Patentability assessment commenced for ${app.title}.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Action failed",
          message: errorMessage(err),
        });
      },
    });
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
          {app.status === "ATTORNEY_ASSIGNED" && (
            <>
              <Button
                size="xs"
                color="teal"
                leftSection={<FaCheck size={10} />}
                loading={respondMutation.isPending}
                aria-label={`Accept assignment for ${app.title}`}
                onClick={() => handleRespond("accept")}
              >
                Accept
              </Button>
              <Button
                size="xs"
                color="red"
                variant="light"
                leftSection={<FaTimes size={10} />}
                loading={respondMutation.isPending}
                aria-label={`Decline assignment for ${app.title}`}
                onClick={() => handleRespond("decline")}
              >
                Decline
              </Button>
            </>
          )}
          {["ATTORNEY_ASSIGNED", "ASSESSMENT_IN_PROGRESS"].includes(app.status) && (
            <Button
              size="xs"
              color="indigo"
              variant="outline"
              leftSection={<FaPlay size={10} />}
              loading={assessmentMutation.isPending}
              aria-label={`Start assessment for ${app.title}`}
              onClick={handleStartAssessment}
            >
              Start Assessment
            </Button>
          )}
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

export default function AttorneyDocketPage() {
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
    ["ATTORNEY_ASSIGNED", "ASSESSMENT_IN_PROGRESS", "PENDING_REVIEW"].includes(app.status),
  );

  return (
    <Container size="lg">
      <PageHeader
        title="Attorney Docket"
        subtitle="Manage panel patent assignments, patentability opinions, and drafting workflows"
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="Docket is empty">
          <Text size="sm">You have no active patent applications in your attorney docket.</Text>
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
              <DocketRow key={app.id} app={app} />
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Container>
  );
}
