import { useEffect, useState } from "react";
import { Alert, Button, Group, Stack, Table, Text, Title } from "@mantine/core";

import { http } from "../../../lib/http";
import type { LeaveRequest } from "../api";

export default function LeaveRequestsPage() {
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    try { setRows((await http.get<{ results: LeaveRequest[] }>("/leave/requests")).data.results); }
    catch { setError("Could not load leave requests."); }
  }
  useEffect(() => { void refresh(); }, []);

  async function decide(id: number, decision: "approved" | "rejected") {
    try { await http.post(`/leave/requests/${id}/review`, { decision }); await refresh(); }
    catch { setError("The request could not be reviewed."); }
  }

  return <Stack p="lg"><Title order={2}>Leave Requests</Title>
    {error && <Alert color="red">{error}</Alert>}
    {rows.length === 0 ? <Text c="dimmed">No leave requests to show.</Text> :
      <Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Employee</Table.Th><Table.Th>Type</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Reason</Table.Th><Table.Th>Status</Table.Th><Table.Th>Decision</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{rows.map((row) => <Table.Tr key={row.id}><Table.Td>{row.employee_name || `Employee #${row.user_id}`}</Table.Td><Table.Td>{row.leave_type_name}</Table.Td><Table.Td>{row.start_date} – {row.end_date}</Table.Td><Table.Td>{row.days}</Table.Td><Table.Td>{row.reason}</Table.Td><Table.Td>{row.status}</Table.Td><Table.Td>{row.status === "pending" && <Group gap="xs"><Button size="xs" onClick={() => void decide(row.id, "approved")}>Approve</Button><Button size="xs" color="red" variant="light" onClick={() => void decide(row.id, "rejected")}>Reject</Button></Group>}</Table.Td></Table.Tr>)}</Table.Tbody>
      </Table>}
  </Stack>;
}
