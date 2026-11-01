import { Badge, Card, Container, Stack, Text, Title, Alert } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { Application, Results } from "../api/types";

export default function MyApplicationsPage() {
  const query = useQuery({
    queryKey: ["gymkhana", "my-applications"],
    queryFn: async () =>
      (await http.get<Results<Application>>("/gymkhana/applications/mine")).data.results,
  });

  return (
    <Container size="lg" py="lg">
      <Stack>
        <Title order={2}>My Membership Applications</Title>
        {query.isLoading && <Text>Loading applications…</Text>}
        {query.isError && <Alert color="red" title="Unable to load applications">Please refresh and try again.</Alert>}
        {query.data?.map((app) => (
          <Card withBorder key={app.id}>
            <Stack gap="xs">
              <Title order={4}>{app.club.name}</Title>
              <Badge color={app.status === "approved" ? "green" : app.status === "rejected" ? "red" : "yellow"}>
                {app.status.toUpperCase()}
              </Badge>
              {app.statement && <Text>{app.statement}</Text>}
              {app.review_remarks && <Text size="sm">Review remarks: {app.review_remarks}</Text>}
              <Text size="xs" c="dimmed">
                Submitted: {new Date(app.created_at).toLocaleString()}
              </Text>
            </Stack>
          </Card>
        ))}
        {query.data?.length === 0 && <Text>You have not applied to any clubs yet.</Text>}
      </Stack>
    </Container>
  );
}
