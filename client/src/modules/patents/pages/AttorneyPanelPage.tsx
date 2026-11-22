import { Alert, Badge, Container, Table, Text } from "@mantine/core";
import { FaInfoCircle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAttorneyPanel } from "../api/hooks";

export default function AttorneyPanelPage() {
  const { data, isPending, error } = useAttorneyPanel();

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

  const attorneys = data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Attorney Panel Management"
        subtitle="Roster of empanelled IP legal counsel, domain specializations, and active drafting capacity"
      />

      {attorneys.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No panel attorneys enrolled">
          <Text size="sm">There are no external patent attorneys currently registered on the institutional panel.</Text>
        </Alert>
      ) : (
        <Table withTableBorder withColumnBorders striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Panel ID</Table.Th>
              <Table.Th>Firm Name</Table.Th>
              <Table.Th>Active Workload</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {attorneys.map((attorney) => (
              <Table.Tr key={attorney.id}>
                <Table.Td>#{attorney.id}</Table.Td>
                <Table.Td fw={500}>{attorney.firm_name}</Table.Td>
                <Table.Td>{attorney.active_workload} active applications</Table.Td>
                <Table.Td>
                  <Badge color={attorney.is_approved_panel ? "green" : "gray"} variant="light">
                    {attorney.is_approved_panel ? "Approved Panel" : "Inactive"}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Container>
  );
}
