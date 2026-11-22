import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function BudgetsPage() {
  return (
    <Container size="xl">
      <PageHeader title="Budget requests" subtitle="Submit and track club budget requests" />
      <Card padding="lg"><Text c="dimmed">No budget requests are currently available.</Text></Card>
    </Container>
  );
}
