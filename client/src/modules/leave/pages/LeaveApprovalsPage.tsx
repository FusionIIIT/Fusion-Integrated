import { useState, useEffect, useCallback } from "react";
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
  Alert,
} from "@mantine/core";
import { http } from "../../../lib/http";

interface LeaveApp {
  id: number;
  user_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  half_day: string;
  days: string;
  reason: string;
  is_station_leave: boolean;
  station_leave_address: string;
  status: string;
}

const LeaveApprovalsPage = () => {
  const [applications, setApplications] = useState<LeaveApp[]>([]);
  const [selectedApplicationId, setSelectedApplicationId] = useState<number | null>(null);
  const [remarks, setRemarks] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchApplications = useCallback(async () => {
    try {
      const response = await http.get("/leave/applications");
      setApplications(response.data);
    } catch (error) {
      console.error("Error fetching leave applications:", error);
    }
  }, []);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const handleReview = async (action: "APPROVE" | "REJECT") => {
    if (!selectedApplicationId) return;
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await http.post(`/leave/applications/${selectedApplicationId}/review`, {
        action,
        remarks,
      });
      setSuccessMsg(`Application #${selectedApplicationId} successfully ${action.toLowerCase()}d.`);
      setSelectedApplicationId(null);
      setRemarks("");
      fetchApplications();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string }; detail?: string } } };
      const msg = e.response?.data?.error?.message || e.response?.data?.detail || `Error performing ${action}.`;
      setErrorMsg(msg);
    }
  };

  return (
    <Container size="lg" py="md">
      <Title order={2} mb="md">Leave Sanction & Approvals</Title>

      {errorMsg && (
        <Alert color="red" mb="md" title="Error">
          {errorMsg}
        </Alert>
      )}

      {successMsg && (
        <Alert color="green" mb="md" title="Success">
          {successMsg}
        </Alert>
      )}

      <Stack gap="sm">
        {applications.length === 0 && (
          <Text c="dimmed">No leave applications currently awaiting review.</Text>
        )}
        {applications.map((app) => (
          <Card key={app.id} shadow="sm" p="md" withBorder>
            <Group justify="space-between" mb="xs">
              <Text fw={700}>
                Application #{app.id} - Employee #{app.user_id} ({app.leave_type})
              </Text>
              <Badge
                color={
                  app.status === "PENDING"
                    ? "yellow"
                    : app.status === "APPROVED"
                    ? "green"
                    : app.status === "REJECTED"
                    ? "red"
                    : "gray"
                }
              >
                {app.status}
              </Badge>
            </Group>
            <Stack gap="xs" my="xs">
              <Text size="sm">
                <strong>Duration:</strong> {app.start_date} to {app.end_date} ({app.days} day(s))
              </Text>
              {app.half_day !== "NONE" && (
                <Text size="sm" c="dimmed">
                  <strong>Half Day:</strong> {app.half_day}
                </Text>
              )}
              <Text size="sm">
                <strong>Reason:</strong> {app.reason}
              </Text>
              {app.is_station_leave && (
                <Text size="sm" c="blue">
                  <strong>Station Contact Address:</strong> {app.station_leave_address}
                </Text>
              )}
            </Stack>

            {app.status === "PENDING" && (
              <Group justify="flex-end" mt="sm">
                <Button
                  size="xs"
                  variant={selectedApplicationId === app.id ? "filled" : "outline"}
                  color="blue"
                  onClick={() => setSelectedApplicationId(app.id)}
                >
                  {selectedApplicationId === app.id ? "Selected for Review" : "Review Decision"}
                </Button>
              </Group>
            )}
          </Card>
        ))}
      </Stack>

      {selectedApplicationId && (
        <Card shadow="md" p="md" mt="lg" withBorder bg="gray.0">
          <Title order={4} mb="sm">
            Reviewing Application #{selectedApplicationId}
          </Title>
          <Stack>
            <TextInput
              label="Review Remarks / Comments"
              placeholder="Enter remarks (optional)..."
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
            <Group gap="sm">
              <Button color="green" onClick={() => handleReview("APPROVE")}>
                Approve Leave
              </Button>
              <Button color="red" onClick={() => handleReview("REJECT")}>
                Reject Leave
              </Button>
              <Button variant="subtle" color="gray" onClick={() => setSelectedApplicationId(null)}>
                Cancel
              </Button>
            </Group>
          </Stack>
        </Card>
      )}
    </Container>
  );
};

export default LeaveApprovalsPage;
