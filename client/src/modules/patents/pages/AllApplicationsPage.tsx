import { useState } from "react";
import { Alert, Button, Container, Group, Modal, NumberInput, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle, FaUserCheck, FaUserTie } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useAssignAttorney, useAssignDirector } from "../api/hooks";
import type { PatentApplicationSummary } from "../api/types";
import { PatentStatusBadge } from "../components/PatentStatusBadge";

function AssignDirectorModal({
  opened,
  onClose,
  application,
}: {
  opened: boolean;
  onClose: () => void;
  application: PatentApplicationSummary;
}) {
  const [directorId, setDirectorId] = useState<number | string>(1);
  const assignMutation = useAssignDirector(application.id);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    assignMutation.mutate(Number(directorId), {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Director assigned",
          message: `Application ${application.title} assigned to Director.`,
        });
        onClose();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Assignment failed",
          message: errorMessage(err),
        });
      },
    });
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Assign Reviewing Director">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm">
            Assign evaluating director for <strong>{application.title}</strong>
          </Text>
          <NumberInput
            label="Director User ID"
            description="Must not share an inventorship COI (BR-PMS-024..027)"
            required
            value={directorId}
            onChange={setDirectorId}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={assignMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={assignMutation.isPending}>
              Assign Director
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function AssignAttorneyModal({
  opened,
  onClose,
  application,
}: {
  opened: boolean;
  onClose: () => void;
  application: PatentApplicationSummary;
}) {
  const [attorneyId, setAttorneyId] = useState<number | string>(1);
  const assignMutation = useAssignAttorney(application.id);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    assignMutation.mutate(Number(attorneyId), {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Attorney assigned",
          message: `Application ${application.title} assigned to Panel Attorney.`,
        });
        onClose();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Assignment failed",
          message: errorMessage(err),
        });
      },
    });
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Assign Panel Attorney">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm">
            Assign drafting attorney for <strong>{application.title}</strong>
          </Text>
          <NumberInput
            label="Attorney Panel ID"
            description="Must be an approved panel member within workload limits (BR-PMS-040..045)"
            required
            value={attorneyId}
            onChange={setAttorneyId}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={assignMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={assignMutation.isPending}>
              Assign Attorney
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export default function AllApplicationsPage() {
  const { data, isPending, error } = useApplications();
  const { can } = useAuth();

  const [directorTarget, setDirectorTarget] = useState<PatentApplicationSummary | null>(null);
  const [attorneyTarget, setAttorneyTarget] = useState<PatentApplicationSummary | null>(null);

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

  const applications = data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="All Patent Applications"
        subtitle="Institutional oversight queue for patent portfolio management and workflow coordination"
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No applications found">
          <Text size="sm">There are no patent applications registered in the institutional repository.</Text>
        </Alert>
      ) : (
        <Table withTableBorder withColumnBorders striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {applications.map((app) => (
              <Table.Tr key={app.id}>
                <Table.Td>{app.application_number || `PMS-${app.id}`}</Table.Td>
                <Table.Td fw={500}>{app.title}</Table.Td>
                <Table.Td>{app.domain_category}</Table.Td>
                <Table.Td>
                  <PatentStatusBadge status={app.status} />
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {can("patents.application.assign_director") &&
                      ["SUBMITTED", "RESUBMITTED"].includes(app.status) && (
                        <Button
                          size="xs"
                          color="cyan"
                          variant="light"
                          leftSection={<FaUserTie size={10} />}
                          aria-label={`Assign director to ${app.title}`}
                          onClick={() => setDirectorTarget(app)}
                        >
                          Assign Director
                        </Button>
                      )}
                    {can("patents.attorney.assign") &&
                      ["APPROVED", "PENDING_REVIEW"].includes(app.status) && (
                        <Button
                          size="xs"
                          color="grape"
                          variant="light"
                          leftSection={<FaUserCheck size={10} />}
                          aria-label={`Assign attorney to ${app.title}`}
                          onClick={() => setAttorneyTarget(app)}
                        >
                          Assign Attorney
                        </Button>
                      )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {directorTarget && (
        <AssignDirectorModal
          opened={Boolean(directorTarget)}
          onClose={() => setDirectorTarget(null)}
          application={directorTarget}
        />
      )}

      {attorneyTarget && (
        <AssignAttorneyModal
          opened={Boolean(attorneyTarget)}
          onClose={() => setAttorneyTarget(null)}
          application={attorneyTarget}
        />
      )}
    </Container>
  );
}
