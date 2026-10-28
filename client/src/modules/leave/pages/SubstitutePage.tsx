import { useEffect, useState } from "react";
import {
  Title,
  Paper,
  Table,
  Button,
  Group,
  Stack,
  Text,
  Badge,
  TextInput,
} from "@mantine/core";
import { leaveApi, type LeaveApplication } from "../api";

export default function SubstitutePage() {
  const [requests, setRequests] = useState<LeaveApplication[]>([]);
  const [remarks, setRemarks] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<boolean>(true);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const data = await leaveApi.getSubstituteRequests();
      setRequests(data);
    } catch (err) {
      console.error("Failed to load substitute requests", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const handleRespond = async (id: number, accept: boolean) => {
    try {
      await leaveApi.respondSubstitute(id, accept, remarks[id] || "");
      loadRequests();
    } catch (err) {
      alert("Failed to record substitute response.");
    }
  };

  return (
    <Stack gap="lg" p="md">
      <Title order={2}>Substitute Responsibility Requests</Title>
      <Paper withBorder radius="md" p="md">
        {requests.length === 0 && !loading ? (
          <Text c="dimmed">No pending substitute requests.</Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Application ID</Table.Th>
                <Table.Th>Applicant User ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Remarks (Optional)</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.map((req) => (
                <Table.Tr key={req.id}>
                  <Table.Td>#{req.id}</Table.Td>
                  <Table.Td>User #{req.user_id}</Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{req.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {req.start_date} to {req.end_date}
                  </Table.Td>
                  <Table.Td>{req.reason || "—"}</Table.Td>
                  <Table.Td>
                    <TextInput
                      placeholder="Remarks..."
                      value={remarks[req.id] || ""}
                      onChange={(e) =>
                        setRemarks({ ...remarks, [req.id]: e.currentTarget.value })
                      }
                      size="xs"
                    />
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        onClick={() => handleRespond(req.id, true)}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        onClick={() => handleRespond(req.id, false)}
                      >
                        Decline
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
}
