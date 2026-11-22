import { Alert, Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useComplaintReport } from "../api/hooks";

export default function ReportsPage() {
  const query = useComplaintReport();
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  return <Container size="lg"><PageHeader title="Complaint Reports" subtitle="Current complaint status and escalation summary." />
    {query.isLoading ? <Text c="dimmed">Loading report…</Text> : <Stack><Card withBorder><Text fw={600}>Complaints by status</Text>{query.data?.complaints_by_status.map((row) => <Group justify="space-between" key={row.status}><Text tt="capitalize">{row.status.replaceAll("_", " ")}</Text><Text fw={600}>{row.total}</Text></Group>)}{!query.data?.complaints_by_status.length && <Alert mt="sm" color="gray">No complaints have been submitted.</Alert>}</Card></Stack>}
  </Container>;
}
