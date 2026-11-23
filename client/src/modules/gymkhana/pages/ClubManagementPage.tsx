import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ClubManagementPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="Club Management" subtitle="Manage bookings, approve membership applications, and create polls." />
        <Card withBorder padding="md">
          <Text size="sm">Club coordinators and co-coordinators can manage their club operations here.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
