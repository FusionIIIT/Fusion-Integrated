import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function FacultyReportsPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="Club Event Reports" subtitle="Review submitted event documentation and activity reports." />
        <Card withBorder padding="md">
          <Text size="sm">Club Faculty Councillors can access and review submitted event reports here.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
