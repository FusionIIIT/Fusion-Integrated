import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function GenericHmPage({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <Container size="xl">
      <PageHeader title={title} subtitle={subtitle} />
      <Card padding="lg">
        <Text c="dimmed">Hostel operations module</Text>
      </Card>
    </Container>
  );
}
