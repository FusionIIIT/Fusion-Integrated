import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ActivityPage() {
  return (
    <Container size="xl">
      <PageHeader title="Club activities" subtitle="Sessions and events" />
      <Card padding="lg"><Text c="dimmed">No activity scheduling controls are available to this role.</Text></Card>
    </Container>
  );
}
