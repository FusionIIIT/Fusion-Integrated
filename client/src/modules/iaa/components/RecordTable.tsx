import { Card, Stack, Table, Text } from "@mantine/core";

import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { FinancialRecord } from "../api/types";

export function RecordTable({ rows, empty, onOpen }: {
  rows: FinancialRecord[];
  empty: string;
  onOpen: (id: number) => void;
}) {
  if (rows.length === 0) {
    return (
      <Card padding="xl">
        <Stack align="center" gap={4}><Text fw={600}>{empty}</Text></Stack>
      </Card>
    );
  }
  return (
    <Card padding={0}>
      <Table highlightOnHover verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>#</Table.Th><Table.Th>Kind</Table.Th><Table.Th>Title / purpose</Table.Th>
            <Table.Th>Department</Table.Th><Table.Th ta="right">Amount</Table.Th>
            <Table.Th>Status</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((r) => (
            <Table.Tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onOpen(r.id)}
              tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") onOpen(r.id); }}
              aria-label={`Open ${r.kind === "ta" ? "TA claim" : "request"} ${r.id}`}>
              <Table.Td>{r.id}</Table.Td>
              <Table.Td>{r.kind === "ta" ? "TA claim" : "Expense / voucher"}</Table.Td>
              <Table.Td>{r.title || r.purpose || "Untitled draft"}</Table.Td>
              <Table.Td>{r.department || "—"}</Table.Td>
              <Table.Td ta="right">{r.amount ?? "—"}</Table.Td>
              <Table.Td><StatusBadge status={r.status} /></Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}
