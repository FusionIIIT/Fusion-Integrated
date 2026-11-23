import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function MembershipsPage() {
  return (
    <Container size="xl">
      <PageHeader title="Membership applications" subtitle="Review open club applications" />
      <Card padding="lg"><Text c="dimmed">No pending membership applications.</Text></Card>
    </Container>
  );
}
