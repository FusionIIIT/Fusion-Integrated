import { useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { useApplyLeave, useLeavePolicies } from "../api/hooks";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const apply = useApplyLeave();
  const { data: policies } = useLeavePolicies();

  const [category, setCategory] = useState<string>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [purpose, setPurpose] = useState<string>("");
  const [isHalfDay, setIsHalfDay] = useState<boolean>(false);
  const [halfDay, setHalfDay] = useState<string>("morning");

  const [stationLeave, setStationLeave] = useState<boolean>(false);
  const [stationCity, setStationCity] = useState<string>("");
  const [stationPurpose, setStationPurpose] = useState<string>("");

  const [substituteId, setSubstituteId] = useState<number | string>("");

  const policyOptions = (policies ?? [
    { category: "CL", name: "Casual Leave" },
    { category: "RH", name: "Restricted Holiday" },
    { category: "SCL", name: "Special Casual Leave" },
    { category: "EL", name: "Earned Leave" },
    { category: "COL", name: "Commuted Leave" },
    { category: "VL", name: "Vacation Leave" },
  ]).map((p) => ({ value: p.category, label: `${p.category} — ${p.name}` }));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!startDate || !endDate || !purpose) {
      notifications.show({
        color: "yellow",
        title: "Missing Required Fields",
        message: "Please fill in leave start date, end date, and purpose.",
      });
      return;
    }

    apply.mutate(
      {
        category,
        leave_start: startDate,
        leave_end: isHalfDay ? startDate : endDate,
        purpose,
        is_half_day: isHalfDay,
        half_day: isHalfDay ? halfDay : "",
        station_leave_required: stationLeave,
        station_leave_city: stationLeave ? stationCity : "",
        station_leave_purpose: stationLeave ? stationPurpose : "",
        substitute_user_id: substituteId ? Number(substituteId) : null,
      },
      {
        onSuccess: (res) => {
          notifications.show({
            color: "green",
            title: "Application Submitted",
            message: `Leave request #${res.id} for ${res.computed_days} days submitted successfully!`,
          });
          navigate("/elm/mine");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Application Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new leave application with dynamic category rules, substitute gate, and station leave coupling (CW-EL-01)"
      />

      <Card withBorder radius="md" padding="xl">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              description="Governed by entitlements in BR-EL-001–009"
              data={policyOptions}
              value={category}
              onChange={(val) => {
                setCategory(val || "CL");
                if (val !== "CL") setIsHalfDay(false);
              }}
              required
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
              {!isHalfDay && (
                <TextInput
                  label="End Date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  required
                />
              )}
            </Group>

            {category === "CL" && (
              <Group>
                <Checkbox
                  label="Half-Day Leave (0.5 CL day)"
                  checked={isHalfDay}
                  onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
                />
                {isHalfDay && (
                  <Select
                    data={[
                      { value: "morning", label: "Morning Session (First Half)" },
                      { value: "afternoon", label: "Afternoon Session (Second Half)" },
                    ]}
                    value={halfDay}
                    onChange={(val) => setHalfDay(val || "morning")}
                    style={{ width: 220 }}
                  />
                )}
              </Group>
            )}

            <Textarea
              label="Purpose of Leave"
              placeholder="Provide a clear description of the reason for absence"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              minRows={3}
              required
            />

            <NumberInput
              label="Nominate Substitute User ID (Optional)"
              description="Coverage responsibility gate (BR-EL-014/015). Must accept before approval proceeds."
              placeholder="e.g. 5"
              value={substituteId}
              onChange={setSubstituteId}
              min={1}
            />

            <Card withBorder radius="sm" padding="sm" bg="gray.0">
              <Checkbox
                label="Station Leave Required (leaving Jabalpur)"
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
                mb={stationLeave ? "xs" : 0}
              />
              {stationLeave && (
                <Stack gap="xs" mt="xs">
                  <TextInput
                    label="Destination City"
                    placeholder="e.g. New Delhi"
                    value={stationCity}
                    onChange={(e) => setStationCity(e.target.value)}
                    required
                  />
                  <TextInput
                    label="Station Leave Purpose / Emergency Contact"
                    placeholder="e.g. Attending academic conference / +91-XXXXXXXXXX"
                    value={stationPurpose}
                    onChange={(e) => setStationPurpose(e.target.value)}
                  />
                </Stack>
              )}
            </Card>

            <Group justify="flex-end" mt="lg">
              <Button variant="default" onClick={() => navigate("/elm/mine")}>
                Cancel
              </Button>
              <Button type="submit" color="blue" loading={apply.isPending}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
