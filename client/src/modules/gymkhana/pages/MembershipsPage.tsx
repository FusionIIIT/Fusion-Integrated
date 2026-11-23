import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function MembershipsPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="My Club Memberships" subtitle="Track your submitted club applications and confirmed enrollments." />
        <Card withBorder padding="md">
          <Text size="sm">Your active club memberships and open application statuses will appear here.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
