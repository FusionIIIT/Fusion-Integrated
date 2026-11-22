import { Badge, Button, Card, Container, Group, Stack, Text, Title } from "@mantine/core";
import { useTriggerMuster } from "../api/hooks";

export default function MusterPage() {
  const triggerMuster = useTriggerMuster();

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        <Title order={2}>Emergency Muster & Campus Evacuation Protocol</Title>

        <Card withBorder padding="md" style={{ borderColor: "red" }}>
          <Title order={4} c="red" mb="xs">Emergency Roll-Call Choke Point</Title>
          <Text mb="md">
            Triggering campus muster immediately locks on-site headcount, flags all active guest passes,
            and alerts security checkpoints for mandatory evacuation headcounts.
          </Text>

          <Group>
            <Button
              color="red"
              size="md"
              loading={triggerMuster.isPending}
              onClick={() => triggerMuster.mutate()}
            >
              Initiate Emergency Muster
            </Button>
          </Group>
        </Card>
      </Stack>
    </Container>
  );
}
