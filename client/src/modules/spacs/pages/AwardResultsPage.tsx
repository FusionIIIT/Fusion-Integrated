import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function AwardResultsPage() {
  return (
    <Container size="xl">
      <PageHeader
        title="Convocation Award Results"
        subtitle="Published institute medals, prizes, and honours"
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          No published convocation award results at this time.
        </Text>
      </Card>
    </Container>
  );
}
