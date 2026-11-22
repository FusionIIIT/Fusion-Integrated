import {
  Card,
  Container,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useConfiguration } from "../api/hooks";

export default function ConfigurationPage() {
  const { data: config, isPending, error } = useConfiguration();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="IAA Policy & Hierarchy Configuration"
          subtitle="Institutional configuration parameters, high-value thresholds, and escalation timeouts."
        />

        {isPending ? (
          <Text>Loading configuration...</Text>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Financial Year
              </Text>
              <Title order={3}>{config?.financial_year}</Title>
            </Card>

            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                High-Value TA Threshold
              </Text>
              <Title order={3}>₹{Number(config?.high_value_ta_threshold).toLocaleString()}</Title>
              <Text size="xs" c="dimmed" mt="xs">
                Claims at or above this require Director/Dean approval.
              </Text>
            </Card>

            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Approval Escalation Timeout
              </Text>
              <Title order={3}>{config?.approval_timeout_days} Days</Title>
              <Text size="xs" c="dimmed" mt="xs">
                Inactivity beyond this duration triggers escalation (IAA-BR-401).
              </Text>
            </Card>
          </SimpleGrid>
        )}
      </Stack>
    </Container>
  );
}
