import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ArchivePage() {
  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Archived Files"
        subtitle="Permanent read-only records of completed file workflows"
      />
      <Stack mt="md">
        <Card withBorder p="md" radius="sm">
          <Text c="dimmed">No archived files found.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
