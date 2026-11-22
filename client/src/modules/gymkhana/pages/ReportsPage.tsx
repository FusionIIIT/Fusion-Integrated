import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ReportsPage() {
  return (
    <Container size="xl">
      <PageHeader title="Event reports" subtitle="Submit and review club event reports" />
      <Card padding="lg"><Text c="dimmed">No event reports are currently available.</Text></Card>
    </Container>
  );
}
