import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
  Collapse,
  Divider,
  Grid,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { leaveApi } from "../api";
import type { LeaveBalance } from "../types";

const CATEGORIES = [
  { value: "CL", label: "Casual Leave (CL) - 8 days/yr, supports half-days" },
  { value: "RH", label: "Restricted Holiday (RH) - 2 days/yr, specific calendar dates" },
  { value: "SCL", label: "Special Casual Leave (SCL) - up to 15 days/yr" },
  { value: "EL", label: "Earned Leave (EL) - 30 days/yr, continuous counting" },
  { value: "COL", label: "Commuted Leave (COL) - 20 days/yr, medical basis" },
  { value: "VL", label: "Vacation Leave (VL) - 60 days/yr, faculty vacation only" },
];

export const ApplyLeavePage: React.FC = () => {
  const navigate = useNavigate();
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loading, setLoading] = useState(false);
  const [category, setCategory] = useState<string>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [halfDay, setHalfDay] = useState<string>("NONE");
  const [reason, setReason] = useState<string>("");
  const [substituteUserId, setSubstituteUserId] = useState<number | "">("");
  const [stationLeave, setStationLeave] = useState<boolean>(false);
  const [stationAddress, setStationAddress] = useState<string>("");
  const [stationContact, setStationContact] = useState<string>("");
  const [stationStartDate, setStationStartDate] = useState<string>("");
  const [stationEndDate, setStationEndDate] = useState<string>("");
  const [medicalUrl, setMedicalUrl] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    leaveApi
      .getMyBalances()
      .then((data) => setBalances(data))
      .catch(() => {});
  }, []);

  const currentBal = balances.find((b) => b.category === category);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    if (!startDate || !endDate) {
      setErrorMsg("Please select both start and end dates.");
      return;
    }
    if (!reason.trim()) {
      setErrorMsg("Please provide a reason for the leave application.");
      return;
    }

    setLoading(true);
    try {
      await leaveApi.applyLeave({
        category,
        start_date: startDate,
        end_date: endDate,
        half_day: halfDay !== "NONE" ? halfDay : undefined,
        reason,
        substitute_user_id: substituteUserId ? Number(substituteUserId) : null,
        station_leave: stationLeave,
        station_address: stationAddress,
        station_contact: stationContact,
        station_start_date: stationStartDate || null,
        station_end_date: stationEndDate || null,
        medical_certificate_url: medicalUrl,
      });

      notifications.show({
        title: "Leave Applied",
        message: "Your leave application has been submitted successfully.",
        color: "teal",
      });
      navigate("/leave/mine");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error ||
        "Failed to submit leave application.";
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p="md" maw={800} mx="auto">
      <Paper p="lg" withBorder shadow="sm" radius="md">
        <Title order={2} mb="xs">
          Apply for Leave
        </Title>
        <Text c="dimmed" size="sm" mb="lg">
          Submit your leave application. Required substitute consent and approval routing will be
          managed automatically per institute policy.
        </Text>

        {errorMsg && (
          <Alert color="red" title="Submission Error" mb="md" withCloseButton onClose={() => setErrorMsg(null)}>
            {errorMsg}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              required
              data={CATEGORIES}
              value={category}
              onChange={(val) => setCategory(val || "CL")}
              description={
                currentBal
                  ? `Available Balance: ${currentBal.balance} day(s) (Total credited: ${currentBal.credited})`
                  : undefined
              }
            />

            {category === "CL" && (
              <Select
                label="Half-Day Option"
                description="Optional: Half-day Casual Leave consumes 0.5 days on a single date (BR-EL-010)"
                data={[
                  { value: "NONE", label: "Full Day" },
                  { value: "FIRST_HALF", label: "First Half (Morning)" },
                  { value: "SECOND_HALF", label: "Second Half (Afternoon)" },
                ]}
                value={halfDay}
                onChange={(val) => setHalfDay(val || "NONE")}
              />
            )}

            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Start Date"
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="End Date"
                  type="date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </Grid.Col>
            </Grid>

            <NumberInput
              label="Nominate Substitute Employee ID (Optional / Recommended)"
              description="Nominate another employee to take responsibility during absence. Approval routing starts after consent."
              placeholder="e.g. 1002"
              value={substituteUserId}
              onChange={(val) => setSubstituteUserId(val === "" ? "" : Number(val))}
            />

            <Textarea
              label="Reason for Leave"
              required
              minRows={3}
              placeholder="State the purpose or justification for leave..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />

            {category === "COL" && (
              <TextInput
                label="Medical Certificate URL / Document Reference"
                required
                description="Required for Commuted Leave (COL) per BR-EL-009"
                placeholder="https://drive.google.com/... or Document ID"
                value={medicalUrl}
                onChange={(e) => setMedicalUrl(e.target.value)}
              />
            )}

            <Divider my="xs" />

            <Checkbox
              label="Station Leave Permission Required (Leaving Jabalpur)"
              description="Station Leave is coupled directly into this leave application per BR-EL-013"
              checked={stationLeave}
              onChange={(e) => setStationLeave(e.currentTarget.checked)}
            />

            <Collapse in={stationLeave}>
              <Card withBorder p="sm" bg="var(--mantine-color-gray-0)">
                <Stack gap="xs">
                  <Text fw={600} size="sm">
                    Station Leave Details
                  </Text>
                  <TextInput
                    label="Station Destination Address"
                    placeholder="Address during absence from Jabalpur"
                    value={stationAddress}
                    onChange={(e) => setStationAddress(e.target.value)}
                  />
                  <TextInput
                    label="Emergency Contact Number"
                    placeholder="Contact phone number while away"
                    value={stationContact}
                    onChange={(e) => setStationContact(e.target.value)}
                  />
                  <Grid>
                    <Grid.Col span={6}>
                      <TextInput
                        label="Station Departure Date"
                        type="date"
                        value={stationStartDate}
                        onChange={(e) => setStationStartDate(e.target.value)}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <TextInput
                        label="Station Return Date"
                        type="date"
                        value={stationEndDate}
                        onChange={(e) => setStationEndDate(e.target.value)}
                      />
                    </Grid.Col>
                  </Grid>
                </Stack>
              </Card>
            </Collapse>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/leave/mine")}>
                Cancel
              </Button>
              <Button type="submit" loading={loading} color="teal">
                Submit Leave Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
};

export default ApplyLeavePage;
