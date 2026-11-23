import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ClubAdminPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="Club Administration" subtitle="Review new club proposals and approve open clubs." />
        <Card withBorder padding="md">
          <Text size="sm">Student Admin panel to establish and confirm student clubs.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
