import { useEffect, useState } from "react";
import { Badge, Button, Group, Paper, Select, Stack, Table, Text, Title } from "@mantine/core";

type WorkRequest = {
  id: number;
  title: string;
  location: string;
  category: string;
  priority: string;
  status: string;
  requester_username: string;
  created_at: string;
};

const STATUS_COLOR: Record<string, string> = {
  draft: "gray", submitted: "blue", under_review: "yellow",
  approved: "teal", rejected: "red", in_progress: "orange",
  on_hold: "grape", completed: "green", closed: "dark",
};

export default function WorkRequestsPage() {
  const [requests, setRequests] = useState<WorkRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/iwd/requests/")
      .then((r) => r.json())
      .then((data) => { setRequests(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = filterStatus
    ? requests.filter((r) => r.status === filterStatus)
    : requests;

  if (loading) return <Text>Loading work requests...</Text>;

  return (
    <Stack gap="md" p="md">
      <Group justify="space-between">
        <Title order={2}>Work Requests</Title>
        <Select
          placeholder="Filter by status"
          clearable
          data={["draft","submitted","under_review","approved","rejected","in_progress","on_hold","completed","closed"]}
          value={filterStatus}
          onChange={setFilterStatus}
          w={200}
        />
      </Group>
      <Paper shadow="xs" withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Location</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Priority</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Submitted By</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {filtered.map((wr) => (
              <Table.Tr key={wr.id}>
                <Table.Td>WR-{wr.id}</Table.Td>
                <Table.Td>{wr.title}</Table.Td>
                <Table.Td>{wr.location}</Table.Td>
                <Table.Td>{wr.category}</Table.Td>
                <Table.Td>
                  <Badge color={wr.priority === "urgent" ? "red" : wr.priority === "high" ? "orange" : "gray"}>
                    {wr.priority}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Badge color={STATUS_COLOR[wr.status] ?? "gray"}>{wr.status.replace("_", " ")}</Badge>
                </Table.Td>
                <Table.Td>{wr.requester_username}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {filtered.length === 0 && (
          <Text ta="center" c="dimmed" p="md">No work requests found.</Text>
        )}
      </Paper>
    </Stack>
  );
}

