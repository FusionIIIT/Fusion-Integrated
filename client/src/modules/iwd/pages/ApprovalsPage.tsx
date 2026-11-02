import { useEffect, useState } from "react";
import { Badge, Button, Group, Modal, Paper, Stack, Table, Text, Textarea, Title } from "@mantine/core";

type WorkRequest = {
  id: number; title: string; location: string;
  category: string; priority: string; status: string;
  estimated_cost: string; requester_username: string;
};

export default function ApprovalsPage() {
  const [requests, setRequests] = useState<WorkRequest[]>([]);
  const [selected, setSelected] = useState<WorkRequest | null>(null);
  const [note, setNote] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const load = () => {
    fetch("/api/v1/iwd/requests/")
      .then((r) => r.json())
      .then((data) => setRequests(data.filter((r: WorkRequest) => ["submitted","under_review"].includes(r.status))));
  };

  useEffect(() => { load(); }, []);

  const act = async (action: string) => {
    if (!selected) return;
    const body: Record<string, string> = { note };
    if (action === "approve" && assignedTo) body.assigned_to = assignedTo;
    await fetch(`/api/v1/iwd/requests/${selected.id}/${action}/`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setSelected(null); setNote(""); setAssignedTo(""); load();
  };

  return (
    <Stack gap="md" p="md">
      <Title order={2}>Pending Approvals</Title>
      <Paper shadow="xs" withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th><Table.Th>Title</Table.Th>
              <Table.Th>Location</Table.Th><Table.Th>Priority</Table.Th>
              <Table.Th>Est. Cost</Table.Th><Table.Th>Requested By</Table.Th>
              <Table.Th>Status</Table.Th><Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>WR-{r.id}</Table.Td>
                <Table.Td>{r.title}</Table.Td>
                <Table.Td>{r.location}</Table.Td>
                <Table.Td><Badge color={r.priority === "urgent" ? "red" : "gray"}>{r.priority}</Badge></Table.Td>
                <Table.Td>Rs. {r.estimated_cost}</Table.Td>
                <Table.Td>{r.requester_username}</Table.Td>
                <Table.Td>{r.status.replace("_"," ")}</Table.Td>
                <Table.Td>
                  <Button size="xs" onClick={() => setSelected(r)}>Review</Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {requests.length === 0 && <Text ta="center" c="dimmed" p="md">No pending approvals.</Text>}
      </Paper>
      <Modal opened={!!selected} onClose={() => setSelected(null)} title={`Review: ${selected?.title}`}>
        <Stack>
          <Textarea label="Note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add remarks..." />
          <Group justify="flex-end">
            <Button color="red" onClick={() => act("reject")}>Reject</Button>
            <Button color="yellow" onClick={() => act("review")}>Mark Under Review</Button>
            <Button color="green" onClick={() => act("approve")}>Approve</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

