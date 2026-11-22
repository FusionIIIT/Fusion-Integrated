import { Button, Card, Container, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { FaDownload } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useExport, useSummary } from "../api/hooks";
import { done, failed } from "../components/toast";

function Counts({ title, rows, cols }: {
  title: string; rows: Record<string, string | number>[]; cols: string[];
}) {
  return (
    <Card padding="md">
      <Title order={5} mb="xs">{title}</Title>
      {rows.length === 0 ? <Text size="sm" c="dimmed">Nothing in your scope.</Text> : (
        <Table>
          <Table.Thead><Table.Tr>{cols.map((c) => <Table.Th key={c}>{c.replace(/_/g, " ")}
          </Table.Th>)}</Table.Tr></Table.Thead>
          <Table.Tbody>{rows.map((r, i) => (
            <Table.Tr key={i}>{cols.map((c) => <Table.Td key={c}>{String(r[c])}</Table.Td>)}
            </Table.Tr>))}</Table.Tbody>
        </Table>
      )}
    </Card>
  );
}

export default function ReportsPage() {
  const { data, isPending, error } = useSummary();
  const exporter = useExport();
  const { can } = useAuth();
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  return (
    <Container size="lg">
      <PageHeader title="Reports" subtitle="Read-only, limited to your active role's scope"
        action={can("iaa.report.export") && (
          <Button leftSection={<FaDownload size={12} />} loading={exporter.isPending}
            onClick={() => exporter.mutateAsync().then(() => done("Export downloaded."))
              .catch(failed)}>Export CSV</Button>)} />
      {isPending || !data ? <Text c="dimmed">Loading…</Text> : (
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Counts title="Requests and claims" rows={data.records}
              cols={["kind", "status", "count"]} />
            <Counts title="Approval turnaround" rows={data.approval_turnaround}
              cols={["designation", "decisions", "average_hours"]} />
            <Counts title="Anomalies" rows={data.anomalies}
              cols={["category", "status", "count"]} />
            <Counts title="Audit observations" rows={data.observations}
              cols={["status", "count"]} />
          </SimpleGrid>
        </Stack>
      )}
    </Container>
  );
}
