import { useEffect, useState } from "react";
import { Badge, Card, Container, Table, Text, Select } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { rspcApi } from "../api/client";
import type { Project, ProjectFundTransaction } from "../api/types";

export default function FinanceLedgerPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<ProjectFundTransaction[]>([]);

  useEffect(() => {
    rspcApi
      .getProjects()
      .then((res) => {
        setProjects(res.data);
        const first = res.data[0];
        if (first) {
          setSelectedProjectId(String(first.id));
        }
      })
      .catch((e) => notifications.show({ color: "red", message: e.message || "Failed to load projects" }));
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      rspcApi
        .getLedger(Number(selectedProjectId))
        .then((res) => setTransactions(res.data))
        .catch((e) => notifications.show({ color: "red", message: e.message || "Failed to load transactions" }));
    }
  }, [selectedProjectId]);

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Financial Ledger"
        subtitle="Append-only transaction ledger and budget head tracking across sanctioned grants"
      />

      <Card withBorder shadow="sm" radius="md" mt="md">
        <Select
          label="Select Project"
          placeholder="Choose project code"
          data={projects.map((p) => ({ value: String(p.id), label: `${p.project_code} - ${p.title}` }))}
          value={selectedProjectId}
          onChange={setSelectedProjectId}
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
            {transactions.length === 0 ? (
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
                    <Badge color={tx.transaction_type === "allocation" ? "teal" : "blue"}>{tx.transaction_type}</Badge>
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
    </Container>
  );
}
