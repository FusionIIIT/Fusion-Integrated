import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCreateVacationSurvey, useVacationSurveys } from "../api/hooks";

export default function SurveyManagementPage() {
  const { data: surveys, isLoading, error } = useVacationSurveys();
  const createSurvey = useCreateVacationSurvey();

  const [vacation, setVacation] = useState("");
  const [deadline, setDeadline] = useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!vacation || !deadline) return;

    createSurvey.mutate(
      { vacation, response_deadline: deadline },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Survey Created", message: `Vacation survey created for ${vacation}.` });
          setVacation("");
          setDeadline("");
        },
        onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Vacation Survey Management" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handleCreate}>
            <Stack gap="sm">
              <Text fw={600}>Create New Vacation Food Continuity Survey</Text>
              <TextInput label="Vacation Name" placeholder="e.g. Winter Break 2026, Diwali Recess" required value={vacation} onChange={(e) => setVacation(e.currentTarget.value)} />
              <TextInput label="Response Deadline" type="datetime-local" required value={deadline} onChange={(e) => setDeadline(e.currentTarget.value)} />
              <Group justify="flex-end">
                <Button type="submit" loading={createSurvey.isPending}>Launch Survey</Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Created Surveys ({surveys?.length ?? 0})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : !surveys || surveys.length === 0 ? (
            <Alert color="gray">No vacation surveys created yet.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Vacation</Table.Th>
                  <Table.Th>Response Deadline</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {surveys.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td>#{s.id}</Table.Td>
                    <Table.Td>{s.vacation}</Table.Td>
                    <Table.Td>{new Date(s.response_deadline).toLocaleString()}</Table.Td>
                    <Table.Td><StatusBadge status={s.is_open ? "active" : "closed"} /></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
