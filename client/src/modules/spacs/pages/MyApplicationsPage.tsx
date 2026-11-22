import { Card, Container, Text, Title, Stack, Badge, Group } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function MyApplicationsPage() {
  return (
    <Container size="xl">
      <PageHeader
        title="My Applications & Renewals"
        subtitle="Track submitted applications, respond to correction requests, and download summaries"
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          No active scholarship applications found. Browse the catalogue to apply for published schemes.
        </Text>
      </Card>
    </Container>
  );
}
