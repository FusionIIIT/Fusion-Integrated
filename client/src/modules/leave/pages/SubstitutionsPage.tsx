import { Alert, Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubstitutions } from "../api";

export default function SubstitutionsPage() {
  const inbox = useSubstitutions();
  if (inbox.error) return <Container size="md"><ErrorState error={inbox.error} /></Container>;
  return <Container size="md">
    <PageHeader title="Substitute requests" subtitle="Accept or decline responsibility coverage assigned to you." />
    <Stack>
      {(inbox.data?.results ?? []).length === 0 && <Alert color="gray">There are no pending substitute requests.</Alert>}
      {(inbox.data?.results ?? []).map((request) => <Card key={request.id} withBorder>
        <Group justify="space-between">
          <div><Text fw={600}>{request.category_code} · {request.start_date} to {request.end_date}</Text>
            <Text size="sm" c="dimmed">Applicant #{request.employee_id} · {request.reason}</Text></div>
          <Group>
            <Button size="xs" color="green" onClick={() => inbox.respond.mutate({ id: request.id, decision: "accept" }, { onError: (e) => notifications.show({ color: "red", title: "Could not accept request", message: errorMessage(e) }) })}>Accept</Button>
            <Button size="xs" color="red" variant="light" onClick={() => inbox.respond.mutate({ id: request.id, decision: "decline" }, { onError: (e) => notifications.show({ color: "red", title: "Could not decline request", message: errorMessage(e) }) })}>Decline</Button>
          </Group>
        </Group>
      </Card>)}
    </Stack>
  </Container>;
}
