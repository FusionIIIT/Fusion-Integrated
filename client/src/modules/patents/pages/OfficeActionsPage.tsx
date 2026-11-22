import { useState } from "react";
import { Alert, Button, Container, Group, Modal, Stack, Table, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle, FaPaperPlane } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useOfficeActionResponse } from "../api/hooks";
import { PatentStatusBadge } from "../components/PatentStatusBadge";

function ResponseModal({
  opened,
  onClose,
  actionId,
  title,
}: {
  opened: boolean;
  onClose: () => void;
  actionId: number;
  title: string;
}) {
  const [summary, setSummary] = useState("");
  const responseMutation = useOfficeActionResponse(actionId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!summary.trim()) {
      notifications.show({
        color: "red",
        title: "Response required",
        message: "A summary response must be entered.",
      });
      return;
    }
    responseMutation.mutate(
      { response_summary: summary.trim() },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Response submitted",
            message: `Response submitted for ${title}.`,
          });
          setSummary("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Response submission failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Respond to Office Action">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm">
            Submitting formal response for <strong>{title}</strong>
          </Text>
          <Textarea
            label="Response Summary"
            placeholder="Detail the technical arguments and claim amendments in response to the examiner objections..."
            required
            minRows={4}
            value={summary}
            onChange={(e) => setSummary(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={responseMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={responseMutation.isPending}>
              Submit Response
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export default function OfficeActionsPage() {
  const { data, isPending, error } = useApplications();
  const [respondTarget, setRespondTarget] = useState<{ id: number; title: string } | null>(null);

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
    ["FILED", "OFFICE_ACTION_PENDING", "RESPONSE_SUBMITTED"].includes(app.status),
  );

  return (
    <Container size="lg">
      <PageHeader
        title="Office Actions & Examination"
        subtitle="Manage official patent office examination reports, objections, and response deadlines"
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No pending office actions">
          <Text size="sm">There are no external patent office examination actions currently awaiting response.</Text>
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
              <Table.Tr key={app.id}>
                <Table.Td>{app.application_number || `PMS-${app.id}`}</Table.Td>
                <Table.Td fw={500}>{app.title}</Table.Td>
                <Table.Td>
                  <PatentStatusBadge status={app.status} />
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      leftSection={<FaPaperPlane size={10} />}
                      aria-label={`Respond to action for ${app.title}`}
                      onClick={() => setRespondTarget({ id: app.id, title: app.title })}
                    >
                      Respond
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {respondTarget && (
        <ResponseModal
          opened={Boolean(respondTarget)}
          onClose={() => setRespondTarget(null)}
          actionId={respondTarget.id}
          title={respondTarget.title}
        />
      )}
    </Container>
  );
}
