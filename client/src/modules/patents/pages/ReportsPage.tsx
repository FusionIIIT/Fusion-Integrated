import { Card, Container, SimpleGrid, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReports } from "../api/hooks";

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string | null | undefined;
  hint?: string;
}) {
  return (
    <Card padding="lg" withBorder>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={700} size="xl" mt={4}>
        {value ?? "—"}
      </Text>
      {hint && (
        <Text size="xs" c="dimmed" mt={4}>
          {hint}
        </Text>
      )}
    </Card>
  );
}

export default function ReportsPage() {
  const { data, isPending, error } = useReports();

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  if (isPending) {
    return (
      <Container size="lg">
        <Text c="dimmed">Loading…</Text>
      </Container>
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Patent Reports & Analytics"
        subtitle="Institutional intellectual property performance metrics and portfolio analytics"
      />

      <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
        <MetricCard
          label="Total Inventions Disclosed"
          value={data?.total_applications ?? 0}
          hint="All submissions received across institute domains"
        />
        <MetricCard
          label="Officially Filed Patents"
          value={data?.filed_count ?? 0}
          hint="Successfully submitted to national/PCT patent offices"
        />
        <MetricCard
          label="Patents Granted"
          value={data?.granted_count ?? 0}
          hint="Formally awarded institutional patent rights"
        />
      </SimpleGrid>
    </Container>
  );
}
