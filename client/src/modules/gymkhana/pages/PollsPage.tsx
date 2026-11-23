import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function PollsPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="Voting Polls" subtitle="Participate in active club decision polls and student voting." />
        <Card withBorder padding="md">
          <Text size="sm">Available polls targeted to your batch and branch will appear here.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
