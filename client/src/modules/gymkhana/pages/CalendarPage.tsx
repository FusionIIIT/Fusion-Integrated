import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function CalendarPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="Events & Sessions" subtitle="View upcoming club sessions, workshops, and campus events." />
        <Card withBorder padding="md">
          <Text size="sm">Booked sessions and events across campus venues appear here.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
