import { Card, Container, Group, Badge, Text, Title, Stack, Button, SimpleGrid } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function CataloguePage() {
  return (
    <Container size="xl">
      <PageHeader
        title="Awards & Scholarships"
        subtitle="Browse available scholarship schemes and convocation awards"
      />
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt="md">
        <Card withBorder shadow="sm" radius="md" p="md">
          <Group justify="space-between" mb="xs">
            <Title order={4}>Merit-cum-Means (MCM) Scholarship</Title>
            <Badge color="green">Active</Badge>
          </Group>
          <Text size="sm" c="dimmed">
            Tuition waiver and monthly allowance for eligible students based on academic performance and family income.
          </Text>
          <Stack mt="md" gap="xs">
            <Text size="xs"><b>Eligibility:</b> CPI ≥ 6.5, Annual parental income ≤ ₹6,00,000</Text>
            <Text size="xs"><b>Application Window:</b> Open for 2026-27 cycle</Text>
          </Stack>
        </Card>

        <Card withBorder shadow="sm" radius="md" p="md">
          <Group justify="space-between" mb="xs">
            <Title order={4}>Director's Gold Medal</Title>
            <Badge color="blue">Award</Badge>
          </Group>
          <Text size="sm" c="dimmed">
            Awarded to the outstanding graduating student across all disciplines for exemplary academic and co-curricular merit.
          </Text>
          <Stack mt="md" gap="xs">
            <Text size="xs"><b>Selection:</b> Institute Committee Evaluation</Text>
            <Text size="xs"><b>Cycle:</b> Convocation 2026</Text>
          </Stack>
        </Card>
      </SimpleGrid>
    </Container>
  );
}
