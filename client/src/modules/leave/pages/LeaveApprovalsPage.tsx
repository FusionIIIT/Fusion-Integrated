import { useState, useEffect } from "react";
import {
  Container,
  Title,
  Card,
  Group,
  Stack,
  Text,
  Button,
  Badge,
  TextInput,
} from "@mantine/core";
import { http } from "../../../lib/http";

interface LeaveApp {
  id: number;
  user_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  days: string;
  reason: string;
  status: string;
}

const LeaveApprovalsPage = () => {
  const [applications, setApplications] = useState<LeaveApp[]>([]);
  const [selectedApplicationId, setSelectedApplicationId] = useState<number | null>(null);
  const [remarks, setRemarks] = useState("");

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const response = await http.get("/leave/applications");
        setApplications(response.data);
      } catch (error) {
        console.error("Error fetching leave applications:", error);
      }
    };

    fetchApplications();
  }, []);

  const handleApprove = async () => {
    if (!selectedApplicationId) return;

    try {
      await http.post(`/leave/applications/${selectedApplicationId}/review`, {
        action: "APPROVE",
        remarks,
      });
      setSelectedApplicationId(null);
      setRemarks("");
      const response = await http.get("/leave/applications");
      setApplications(response.data);
    } catch (error) {
      console.error("Error approving leave application:", error);
    }
  };

  const handleReject = async () => {
    if (!selectedApplicationId) return;

    try {
      await http.post(`/leave/applications/${selectedApplicationId}/review`, {
        action: "REJECT",
        remarks,
      });
      setSelectedApplicationId(null);
      setRemarks("");
      const response = await http.get("/leave/applications");
      setApplications(response.data);
    } catch (error) {
      console.error("Error rejecting leave application:", error);
    }
  };

  return (
    <Container size="lg" p="md">
      <Title order={2} mb="md">Leave Approvals</Title>
      <Stack gap="sm">
        {applications.map((app) => (
          <Card key={app.id} shadow="sm" p="sm">
            <Group justify="space-between">
              <Text>Employee #{app.user_id}</Text>
              <Badge color={app.status === "PENDING" ? "yellow" : "green"}>{app.status}</Badge>
            </Group>
            <Stack gap="xs" my="xs">
              <Text>{app.leave_type} - {app.start_date} to {app.end_date}</Text>
              <Text>{app.reason}</Text>
            </Stack>
            <Button
              variant="outline"
              color={app.status === "PENDING" ? "yellow" : "green"}
              onClick={() => setSelectedApplicationId(app.id)}
              disabled={app.status !== "PENDING"}
            >
              Review
            </Button>
          </Card>
        ))}
      </Stack>

      <Group justify="center" mt="lg">
        {selectedApplicationId && (
          <>
            <TextInput
              label="Remarks"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
            <Group gap="sm">
              <Button variant="outline" color="green" onClick={handleApprove}>
                Approve
              </Button>
              <Button variant="outline" color="red" onClick={handleReject}>
                Reject
              </Button>
            </Group>
          </>
        )}
      </Group>
    </Container>
  );
};

export default LeaveApprovalsPage;
