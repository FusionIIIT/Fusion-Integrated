import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateLeaveRequest,
  useSubmitLeaveRequest,
} from "../hooks/useLeaveRequests";
import type { LeaveCategory, LeaveRequestCreate } from "../api/types";

const CATEGORIES: { value: LeaveCategory; label: string }[] = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
];

const HALF_DAY_SESSIONS = [
  { value: "forenoon", label: "Forenoon" },
  { value: "afternoon", label: "Afternoon" },
];

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const createLeave = useCreateLeaveRequest();
  const submitLeave = useSubmitLeaveRequest();
  const [formData, setFormData] = useState<LeaveRequestCreate>({
    category: "CL",
    start_date: "",
    end_date: "",
    half_day: false,
    half_day_session: "forenoon",
    purpose: "",
    station_leave: false,
    station_leave_address: "",
    substitute_id: null,
  });

  const handleCreate = async () => {
    try {
      await createLeave.mutateAsync(formData);
      notifications.show({
        title: "Draft created",
        message: "Leave request saved as draft",
        color: "green",
      });
      navigate("/leave/my-requests");
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to create leave request",
        color: "red",
      });
    }
  };

  const handleCreateAndSubmit = async () => {
    try {
      const leave = await createLeave.mutateAsync(formData);
      await submitLeave.mutateAsync(leave.id);
      notifications.show({
        title: "Submitted",
        message: "Leave request submitted for approval",
        color: "green",
      });
      navigate("/leave/my-requests");
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to submit leave request",
        color: "red",
      });
    }
  };

  const isRestrictedHoliday = formData.category === "RH";
  const isHalfDayAllowed = formData.category === "CL";
  const requiresSubstitute = ["SCL", "EL", "VL", "COL"].includes(formData.category);

  return (
    <Container size="lg">
      <PageHeader title="Apply for Leave" subtitle="Create a new leave request" />
      <Card padding="lg">
        <Stack gap="md">
          <Select
            label="Leave Category *"
            placeholder="Select leave category"
            value={formData.category}
            onChange={(category) => {
              if (category) {
                setFormData((prev) => ({ ...prev, category: category as LeaveCategory }));
              }
            }}
            data={CATEGORIES}
            required
          />

          <Group grow>
            <TextInput
              type="date"
              label="Start date *"
              value={formData.start_date}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, start_date: event.currentTarget.value }))
              }
              required
            />
            <TextInput
              type="date"
              label="End date *"
              value={formData.end_date}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, end_date: event.currentTarget.value }))
              }
              required
            />
          </Group>

          {isHalfDayAllowed && (
            <Checkbox
              label="Half day"
              checked={formData.half_day}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, half_day: event.currentTarget.checked }))
              }
            />
          )}

          {formData.half_day && isHalfDayAllowed && (
            <Select
              label="Session"
              placeholder="Select session"
              value={formData.half_day_session}
              onChange={(session) => {
                if (session === "forenoon" || session === "afternoon") {
                  setFormData((prev) => ({ ...prev, half_day_session: session }));
                }
              }}
              data={HALF_DAY_SESSIONS}
              required
            />
          )}

          <Textarea
            label="Purpose *"
            placeholder="Enter purpose of leave"
            value={formData.purpose}
            onChange={(event) =>
              setFormData((prev) => ({ ...prev, purpose: event.currentTarget.value }))
            }
            minRows={3}
            required
          />

          <Checkbox
            label="Station leave (outside Jabalpur)"
            checked={formData.station_leave}
            onChange={(event) =>
              setFormData((prev) => ({ ...prev, station_leave: event.currentTarget.checked }))
            }
          />

          {formData.station_leave && (
            <Textarea
              label="Station leave address"
              placeholder="Enter address during leave"
              value={formData.station_leave_address}
              onChange={(event) =>
                setFormData((prev) => ({
                  ...prev,
                  station_leave_address: event.currentTarget.value,
                }))
              }
              minRows={2}
            />
          )}

          {requiresSubstitute && (
            <TextInput
              label="Substitute Employee ID *"
              placeholder="Enter substitute's employee ID"
              type="number"
              value={formData.substitute_id?.toString() ?? ""}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setFormData((prev) => ({
                  ...prev,
                  substitute_id: value ? Number(value) : null,
                }));
              }}
              required
            />
          )}

          {isRestrictedHoliday && (
            <Text c="dimmed" size="sm">
              Note: Restricted Holiday must be a published RH date.
            </Text>
          )}

          <Group>
            <Button onClick={handleCreate} loading={createLeave.isPending}>
              Save as Draft
            </Button>
            <Button
              onClick={handleCreateAndSubmit}
              loading={submitLeave.isPending}
              color="blue"
            >
              Submit for Approval
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
