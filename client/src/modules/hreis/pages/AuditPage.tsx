import { Card, Container, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditEvents, useComplianceRequests } from "../api/hooks";

export default function AuditPage() {
  const { data, error, isPending } = useAuditEvents();
  const {
    data: compliance, error: complianceError, isPending: compliancePending,
  } = useComplianceRequests();
  return (
    <Container size="xl">
      <PageHeader title="HR Audit" subtitle="Restricted, timestamped HR activity" />
      {error && <ErrorState error={error} />}
      {isPending && <Text c="dimmed">Loading audit records...</Text>}
      {data && <Card withBorder>
        {data.results.length === 0
          ? <Text c="dimmed">No audited transactions have been recorded.</Text>
          : <Table.ScrollContainer minWidth={700}>
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr>
                <Table.Th>Time</Table.Th><Table.Th>Actor</Table.Th>
                <Table.Th>Action</Table.Th><Table.Th>Resource</Table.Th>
                <Table.Th>Revision</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>{data.results.map((event) => (
                <Table.Tr key={event.id}>
                  <Table.Td>{new Date(event.recorded_at).toLocaleString()}</Table.Td>
                  <Table.Td>{event.acting_designation} #{event.actor_user_id}</Table.Td>
                  <Table.Td>{event.action}</Table.Td>
                  <Table.Td>{event.resource_kind} #{event.resource_id}</Table.Td>
                  <Table.Td>{event.data.revision ?? "�"}</Table.Td>
                </Table.Tr>
              ))}</Table.Tbody>
            </Table>
          </Table.ScrollContainer>}
      </Card>}
      <Card withBorder mt="lg">
        <Text fw={700} mb="xs">Request compliance status</Text>
        <Text size="sm" c="dimmed" mb="md">
          Historical statuses only. Medical reasons, appraisal forms and claim
          evidence are excluded from this view.
        </Text>
        {complianceError && <ErrorState error={complianceError} />}
        {compliancePending && <Text c="dimmed">Loading compliance statuses...</Text>}
        {compliance && (
          compliance.results.length === 0
            ? <Text c="dimmed">No request compliance statuses recorded.</Text>
            : <Table.ScrollContainer minWidth={580}>
              <Table striped>
                <Table.Thead><Table.Tr>
                  <Table.Th>Request ID</Table.Th>
                  <Table.Th>Employee ID</Table.Th>
                  <Table.Th>Family</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Submitted</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>{compliance.results.map((entry) => (
                  <Table.Tr key={entry.id}>
                    <Table.Td>#{entry.id}</Table.Td>
                    <Table.Td>#{entry.user_id}</Table.Td>
                    <Table.Td>{entry.family.toUpperCase()}</Table.Td>
                    <Table.Td>{entry.state.replaceAll("_", " ")}</Table.Td>
                    <Table.Td>{entry.submitted_at
                      ? new Date(entry.submitted_at).toLocaleDateString()
                      : "Not submitted"}</Table.Td>
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
            </Table.ScrollContainer>
        )}
      </Card>
    </Container>
  );
}
