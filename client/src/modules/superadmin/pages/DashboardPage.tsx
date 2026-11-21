import { Badge, Card, Container, Grid, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { FaArchive, FaClipboardList, FaScroll, FaTrash } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboard } from "../api/hooks";

const STAT_ICONS: Record<string, React.ReactNode> = {
  "Archived Users": <FaArchive size={20} />,
  "Reversible Users": <FaArchive size={20} />,
  "Pending Purges": <FaTrash size={20} />,
  "Total Audit Events": <FaScroll size={20} />,
};

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap={4}>
        <Group gap={6}>
          {STAT_ICONS[label] ?? <FaClipboardList size={20} />}
          <Text size="sm" c="dimmed">{label}</Text>
        </Group>
        <Title order={3}>{value}</Title>
      </Stack>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, isPending, error } = useDashboard();

  if (isPending) return <Container size="xl"><Loader mt="xl" /></Container>;
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const m = data!;

  return (
    <Container size="xl">
      <PageHeader
        title="System Administration"
        subtitle="Governance overview and operational metrics"
      />

      <Grid>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatCard label="Archived Users" value={m.archived_users_total} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatCard label="Reversible Users" value={m.archived_users_reversible} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatCard label="Pending Purges" value={m.purge_requests_pending} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatCard label="Total Audit Events" value={m.audit_logs_total} />
        </Grid.Col>
      </Grid>

      <Card withBorder mt="xl" padding="md">
        <Text size="sm" c="dimmed" mb="xs">Status</Text>
        <Group gap="xs">
          <Badge color="green">IAM: Fusion_System_Administrator</Badge>
          <Badge color="blue">Governance: Fusion-Integrated</Badge>
        </Group>
      </Card>
    </Container>
  );
}
