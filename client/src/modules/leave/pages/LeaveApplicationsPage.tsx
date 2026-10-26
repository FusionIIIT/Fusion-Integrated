import { useState, useEffect, useCallback } from "react";
import {
  Container,
  Title,
  Card,
  Group,
  Stack,
  Text,
  Button,
  Select,
  TextInput,
  Textarea,
  Checkbox,
  Badge,
  SimpleGrid,
  Alert,
} from "@mantine/core";
import { http } from "../../../lib/http";
import { useAuth } from "../../../auth/AuthProvider";

interface LeaveBalance {
  id: number;
  leave_type: string;
  allocated: string;
  used: string;
  available: string;
}

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
  reviewed_by?: number | null;
  review_remarks?: string;
}

const LEAVE_TYPES = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
];

const HALF_DAY_OPTIONS = [
  { value: "NONE", label: "Full Day / Multiple Days" },
  { value: "FIRST_HALF", label: "First Half (0.5 day - CL only)" },
  { value: "SECOND_HALF", label: "Second Half (0.5 day - CL only)" },
];

const LeaveApplicationsPage = () => {
  const [applications, setApplications] = useState<LeaveApp[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    leave_type: "CL",
    start_date: "",
    end_date: "",
    half_day: "NONE",
    reason: "",
    is_station_leave: false,
    station_leave_address: "",
  });
  const { session } = useAuth();

  const loadData = useCallback(() => {
    http.get("/leave/balances")
      .then((res) => setBalances(res.data))
      .catch((err) => console.error(err));
    http.get("/leave/applications")
      .then((res) => setApplications(res.data))
      .catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    loadData();
  }, [session, loadData]);

  const handleSubmit = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await http.post("/leave/applications", formData);
      setSuccessMsg("Leave application submitted successfully.");
      setFormData({
        leave_type: "CL",
        start_date: "",
        end_date: "",
        half_day: "NONE",
        reason: "",
        is_station_leave: false,
        station_leave_address: "",
      });
      loadData();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string }; detail?: string } } };
      const msg = e.response?.data?.error?.message || e.response?.data?.detail || "Error submitting leave application.";
      setErrorMsg(msg);
    }
  };

  const handleWithdraw = async (id: number) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await http.post(`/leave/applications/${id}/withdraw`);
      setSuccessMsg(`Application #${id} withdrawn.`);
      loadData();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setErrorMsg(e.response?.data?.error?.message || "Error withdrawing application.");
    }
  };

  const handleCancel = async (id: number) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await http.post(`/leave/applications/${id}/cancel`);
      setSuccessMsg(`Application #${id} cancelled and balance restored.`);
      loadData();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setErrorMsg(e.response?.data?.error?.message || "Error cancelling application.");
    }
  };

  return (
    <Container size="lg" py="md">
      <Title order={2} mb="md">Employee Leave Management</Title>

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

      {balances.length > 0 && (
        <Card shadow="sm" p="md" mb="md" withBorder>
          <Text fw={600} mb="xs">Available Leave Balances</Text>
          <Group>
            {balances.map((b) => (
              <Badge key={b.id} size="lg" variant="light" color="blue">
                {b.leave_type}: {b.available ?? (Number(b.allocated) - Number(b.used))} / {b.allocated} left
              </Badge>
            ))}
          </Group>
        </Card>
      )}

      <Card shadow="sm" p="md" mb="lg" withBorder>
        <Title order={4} mb="sm">Apply for Leave</Title>
        <Stack>
          <Group grow>
            <Select
              label="Leave Type"
              placeholder="Select leave type"
              value={formData.leave_type}
              onChange={(value) => setFormData({ ...formData, leave_type: value || "CL" })}
              data={LEAVE_TYPES}
            />
            <Select
              label="Half-Day Option"
              value={formData.half_day}
              onChange={(value) => setFormData({ ...formData, half_day: value || "NONE" })}
              data={HALF_DAY_OPTIONS}
              disabled={formData.leave_type !== "CL"}
            />
          </Group>

          <Group grow>
            <TextInput
              label="Start Date"
              placeholder="YYYY-MM-DD"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            />
            <TextInput
              label="End Date"
              placeholder="YYYY-MM-DD"
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
            />
          </Group>

          <Textarea
            label="Reason for Leave"
            placeholder="Specify reason..."
            value={formData.reason}
            onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
            minRows={2}
          />

          <Checkbox
            label="Station Leave (travelling outside station)"
            checked={formData.is_station_leave}
            onChange={() =>
              setFormData({ ...formData, is_station_leave: !formData.is_station_leave })
            }
          />

          {formData.is_station_leave && (
            <TextInput
              label="Station Leave Contact Address"
              placeholder="Full address during travel"
              value={formData.station_leave_address}
              onChange={(e) =>
                setFormData({ ...formData, station_leave_address: e.target.value })
              }
            />
          )}

          <Button onClick={handleSubmit} color="blue">
            Submit Application
          </Button>
        </Stack>
      </Card>

      <Title order={3} mb="sm">My Leave Applications</Title>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {applications.map((app) => (
          <Card shadow="sm" p="md" key={app.id} withBorder>
            <Group justify="space-between" mb="xs">
              <Text fw={700}>Application #{app.id} - {app.leave_type}</Text>
              <Badge
                color={
                  app.status === "APPROVED"
                    ? "green"
                    : app.status === "PENDING"
                    ? "yellow"
                    : app.status === "REJECTED"
                    ? "red"
                    : "gray"
                }
              >
                {app.status}
              </Badge>
            </Group>
            <Text size="sm">
              <strong>Period:</strong> {app.start_date} to {app.end_date} ({app.days} day(s))
            </Text>
            {app.half_day !== "NONE" && (
              <Text size="sm" c="dimmed">
                <strong>Half-Day:</strong> {app.half_day}
              </Text>
            )}
            <Text size="sm" mt="xs">
              <strong>Reason:</strong> {app.reason}
            </Text>
            {app.is_station_leave && (
              <Text size="sm" c="blue">
                <strong>Station Address:</strong> {app.station_leave_address}
              </Text>
            )}
            {app.review_remarks && (
              <Text size="sm" c="orange">
                <strong>Review Remarks:</strong> {app.review_remarks}
              </Text>
            )}

            <Group mt="md">
              {app.status === "PENDING" && (
                <Button
                  size="xs"
                  variant="outline"
                  color="red"
                  onClick={() => handleWithdraw(app.id)}
                >
                  Withdraw
                </Button>
              )}
              {app.status === "APPROVED" && (
                <Button
                  size="xs"
                  variant="outline"
                  color="orange"
                  onClick={() => handleCancel(app.id)}
                >
                  Cancel Leave
                </Button>
              )}
            </Group>
          </Card>
        ))}
      </SimpleGrid>
    </Container>
  );
};

export default LeaveApplicationsPage;
