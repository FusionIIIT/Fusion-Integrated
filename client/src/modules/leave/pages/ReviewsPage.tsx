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

export default function ReviewsPage() {
  const [queue, setQueue] = useState<LeaveApplication[]>([]);
  const [remarks, setRemarks] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<boolean>(true);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const data = await leaveApi.getApprovalQueue();
      setQueue(data);
    } catch (err) {
      console.error("Failed to load approval queue", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleUnitHeadAction = async (id: number, approveOrRecommend: boolean) => {
    try {
      await leaveApi.reviewUnitHead(id, approveOrRecommend, remarks[id] || "");
      loadQueue();
    } catch (err) {
      alert("Failed to record Unit Head action.");
    }
  };

  const handleSanctionAction = async (id: number, approve: boolean) => {
    try {
      await leaveApi.decideSanction(id, approve, remarks[id] || "");
      loadQueue();
    } catch (err) {
      alert("Failed to record sanctioning decision.");
    }
  };

  return (
    <Stack gap="lg" p="md">
      <Title order={2}>Leave Review & Approval Queue</Title>
      <Paper withBorder radius="md" p="md">
        {queue.length === 0 && !loading ? (
          <Text c="dimmed">No pending leave applications in your review queue.</Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Applicant</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Current State</Table.Th>
                <Table.Th>Remarks</Table.Th>
                <Table.Th>Decisions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {queue.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td>#{app.id}</Table.Td>
                  <Table.Td>User #{app.user_id}</Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{app.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {app.start_date} to {app.end_date}
                  </Table.Td>
                  <Table.Td>{app.calculated_days}</Table.Td>
                  <Table.Td>{app.reason || "—"}</Table.Td>
                  <Table.Td>
                    <Badge color="yellow">{app.status.replace(/_/g, " ")}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      placeholder="Remarks..."
                      value={remarks[app.id] || ""}
                      onChange={(e) =>
                        setRemarks({ ...remarks, [app.id]: e.currentTarget.value })
                      }
                      size="xs"
                    />
                  </Table.Td>
                  <Table.Td>
                    {app.status === "unit_head_pending" ? (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => handleUnitHeadAction(app.id, true)}
                        >
                          {["CL", "RH"].includes(app.category) ? "Sanction / Approve" : "Recommend"}
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => handleUnitHeadAction(app.id, false)}
                        >
                          {["CL", "RH"].includes(app.category) ? "Reject" : "Not Recommend"}
                        </Button>
                      </Group>
                    ) : app.status === "sanctioning_pending" ? (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => handleSanctionAction(app.id, true)}
                        >
                          Sanction / Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => handleSanctionAction(app.id, false)}
                        >
                          Reject
                        </Button>
                      </Group>
                    ) : null}
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
