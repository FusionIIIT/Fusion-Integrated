import { useState, useEffect } from "react";
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
} from "@mantine/core";
import { http } from "../../../lib/http";
import { useAuth } from "../../../auth/AuthProvider";

interface LeaveBalance {
  id: number;
  leave_type: string;
  allocated: string;
  used: string;
}

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

const LEAVE_TYPES = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
];

const LeaveApplicationsPage = () => {
  const [applications, setApplications] = useState<LeaveApp[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [formData, setFormData] = useState({
    leave_type: "CL",
    start_date: "",
    end_date: "",
    days: "1",
    reason: "",
    is_station_leave: false,
    station_leave_address: "",
  });
  const { session } = useAuth();

  useEffect(() => {
    http.get("/leave/balances").then((res) => setBalances(res.data)).catch(console.error);
    http.get("/leave/applications").then((res) => setApplications(res.data)).catch(console.error);
  }, [session]);

  const handleSubmit = async () => {
    try {
      await http.post("/leave/applications", formData);
      const res = await http.get("/leave/applications");
      setApplications(res.data);
    } catch (error) {
      console.error("Error submitting leave application:", error);
    }
  };

  return (
    <Container>
      <Title order={2} mb="md">Leave Applications</Title>

      {balances.length > 0 && (
        <Card shadow="sm" p="md" mb="md">
          <Group>
            {balances.map((b) => (
              <Badge key={b.id} size="lg" variant="light">
                {b.leave_type}: {Number(b.allocated) - Number(b.used)} / {b.allocated}
              </Badge>
            ))}
          </Group>
        </Card>
      )}

      <Card shadow="sm" p="md" mb="md">
        <Select
          label="Leave Type"
          placeholder="Select leave type"
          value={formData.leave_type}
          onChange={(value) => setFormData({ ...formData, leave_type: value || "CL" })}
          data={LEAVE_TYPES}
        />
      </Card>

      <Card shadow="sm" p="md" mb="lg">
        <Stack>
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
          <TextInput
            label="Days"
            type="number"
            value={formData.days}
            onChange={(e) => setFormData({ ...formData, days: e.target.value })}
          />
          <Textarea
            label="Reason"
            value={formData.reason}
            onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
          />
          <Checkbox
            label="Station Leave"
            checked={formData.is_station_leave}
            onChange={() => setFormData({ ...formData, is_station_leave: !formData.is_station_leave })}
          />
          {formData.is_station_leave && (
            <TextInput
              label="Station Leave Address"
              value={formData.station_leave_address}
              onChange={(e) => setFormData({ ...formData, station_leave_address: e.target.value })}
            />
          )}
          <Button onClick={handleSubmit}>Submit Application</Button>
        </Stack>
      </Card>

      <Title order={3} mb="sm">Submitted Leave Applications</Title>
      <SimpleGrid cols={2} spacing="lg">
        {applications.map((app) => (
          <Card shadow="sm" p="md" key={app.id}>
            <Group justify="space-between">
              <Text>User #{app.user_id}</Text>
              <Badge variant="outline">{app.status}</Badge>
            </Group>
            <Text>Leave Type: {app.leave_type}</Text>
            <Text>Start Date: {app.start_date}</Text>
            <Text>End Date: {app.end_date}</Text>
            <Text>Days: {app.days}</Text>
            <Text>Reason: {app.reason}</Text>
          </Card>
        ))}
      </SimpleGrid>
    </Container>
  );
};

export default LeaveApplicationsPage;
