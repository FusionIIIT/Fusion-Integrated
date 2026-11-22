import { useEffect, useState } from "react";
import { Badge, Card, Container, Select, Stack, Table, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useLedger, useProjects } from "../api/hooks";

export default function FinanceLedgerPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const { data: projects, isLoading: projectsLoading, error: projectsError } = useProjects();

  useEffect(() => {
    if (!selectedProjectId && projects && projects.length > 0) {
      const first = projects[0];
      if (first) {
        setSelectedProjectId(String(first.id));
      }
    }
  }, [projects, selectedProjectId]);

  const projectIdNum = selectedProjectId ? Number(selectedProjectId) : undefined;
  const {
    data: transactions,
    isLoading: transactionsLoading,
    error: transactionsError,
  } = useLedger(projectIdNum);

  const error = projectsError || transactionsError;

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Financial Ledger"
        subtitle="Append-only transaction ledger and budget head tracking across sanctioned grants"
      />

      {error ? (
        <Stack mt="md">
          <ErrorState error={error} />
        </Stack>
      ) : (
        <Card withBorder shadow="sm" radius="md" mt="md">
          <Select
            label="Select Project"
            placeholder="Choose project code"
            data={
              projects?.map((p) => ({
                value: String(p.id),
                label: `${p.project_code} - ${p.title}`,
              })) || []
            }
            value={selectedProjectId}
            onChange={setSelectedProjectId}
            disabled={projectsLoading}
            mb="lg"
          />

          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Tx ID</Table.Th>
                <Table.Th>Budget Head</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Amount</Table.Th>
                <Table.Th>Reference No</Table.Th>
                <Table.Th>Description</Table.Th>
                <Table.Th>Timestamp</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {projectsLoading || transactionsLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">Loading ledger transactions...</Text>
                  </Table.Td>
                </Table.Tr>
              ) : !transactions || transactions.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">No transactions recorded for this project.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                transactions.map((tx) => (
                  <Table.Tr key={tx.id}>
                    <Table.Td>#{tx.id}</Table.Td>
                    <Table.Td>{tx.head_type}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={tx.transaction_type === "allocation" ? "teal" : "blue"}
                      >
                        {tx.transaction_type}
                      </Badge>
                    </Table.Td>
                    <Table.Td fw={600}>₹{Number(tx.amount).toLocaleString("en-IN")}</Table.Td>
                    <Table.Td>{tx.reference_no}</Table.Td>
                    <Table.Td>{tx.description}</Table.Td>
                    <Table.Td>{new Date(tx.created_at).toLocaleString()}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Container>
  );
}
