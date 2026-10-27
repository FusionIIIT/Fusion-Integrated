import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Container,
  Grid,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { FaCheckCircle, FaExclamationTriangle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeave, useLeaveBalances } from "../api/hooks";
import type { LeaveCategory } from "../api/types";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const { data: balances } = useLeaveBalances();
  const applyMutation = useApplyLeave();

  const [category, setCategory] = useState<LeaveCategory>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState<"none" | "FN" | "AN">("none");
  const [purpose, setPurpose] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [substituteUserId, setSubstituteUserId] = useState<number | undefined>(undefined);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const selectedBalance = balances?.find((b) => b.category === category);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!startDate || !endDate) {
      setErrorMsg("Please select both start and end dates.");
      return;
    }

    if (stationLeave && !stationDetails.trim()) {
      setErrorMsg("Station leave requires entering out-of-station destination details (BR-EL-013).");
      return;
    }

    applyMutation.mutate(
      {
        category,
        start_date: startDate,
        end_date: endDate,
        half_day: halfDay,
        half_day_period: halfDay ? halfDayPeriod : "none",
        purpose,
        station_leave: stationLeave,
        station_details: stationDetails,
        substitute_user_id: substituteUserId || null,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            title: "Leave Application Submitted",
            message: `Your request for ${data.days_count} day(s) of ${data.category} has been submitted (Status: ${data.status}).`,
            color: "green",
            icon: <FaCheckCircle />,
          });
          navigate("/leave/my-requests");
        },
        onError: (err: any) => {
          const msg =
            err.response?.data?.detail ||
            err.response?.data?.message ||
            "Failed to submit leave application. Please check balance and overlapping dates.";
          setErrorMsg(msg);
        },
      }
    );
  };

  return (
    <Container size="md" py="md">
      <PageHeader
        title="Apply for Leave"
        description="Submit an official absence request following institute leave regulations (BR-EL-001..020)."
      />

      <Card withBorder radius="md" p="xl" mt="md">
        {errorMsg && (
          <Alert
            icon={<FaExclamationTriangle />}
            title="Validation Error"
            color="red"
            mb="lg"
          >
            {errorMsg}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Grid>
              <Grid.Col span={{ base: 12, sm: 8 }}>
                <Select
                  label="Leave Category"
                  placeholder="Select category"
                  value={category}
                  onChange={(val) => setCategory((val as LeaveCategory) || "CL")}
                  data={[
                    { value: "CL", label: "Casual Leave (CL)" },
                    { value: "RH", label: "Restricted Holiday (RH)" },
                    { value: "SCL", label: "Special Casual Leave (SCL)" },
                    { value: "EL", label: "Earned Leave (EL)" },
                    { value: "COL", label: "Commuted Leave (COL)" },
                    { value: "VL", label: "Vacation Leave (VL)" },
                  ]}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 4 }}>
                <Text size="sm" fw={500} mt={4}>
                  Available Quota
                </Text>
                <Text size="lg" fw={700} c="blue">
                  {selectedBalance ? `${selectedBalance.available} Days` : "—"}
                </Text>
              </Grid.Col>
            </Grid>

            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="Start Date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="End Date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  required
                />
              </Grid.Col>
            </Grid>

            {category === "CL" && (
              <Group mt="xs">
                <Checkbox
                  label="Half-Day Leave (0.5 day debit)"
                  checked={halfDay}
                  onChange={(e) => {
                    setHalfDay(e.currentTarget.checked);
                    if (e.currentTarget.checked && halfDayPeriod === "none") {
                      setHalfDayPeriod("FN");
                    }
                  }}
                />
                {halfDay && (
                  <Select
                    size="xs"
                    value={halfDayPeriod}
                    onChange={(v) => setHalfDayPeriod((v as "FN" | "AN") || "FN")}
                    data={[
                      { value: "FN", label: "Forenoon (First Half)" },
                      { value: "AN", label: "Afternoon (Second Half)" },
                    ]}
                  />
                )}
              </Group>
            )}

            <Group mt="xs">
              <Checkbox
                label="Station Leave (Leaving city/campus)"
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
              />
            </Group>

            {stationLeave && (
              <TextInput
                label="Station Destination & Contact Address"
                placeholder="e.g., Bhopal / Family emergency / Phone: 9876543210"
                value={stationDetails}
                onChange={(e) => setStationDetails(e.target.value)}
                required
              />
            )}

            <NumberInput
              label="Nominated Substitute User ID (Optional)"
              placeholder="e.g., 102"
              description="Leave will pause in awaiting_substitute until consent is given (BR-EL-014..015)."
              value={substituteUserId}
              onChange={(val) => setSubstituteUserId(typeof val === "number" ? val : undefined)}
            />

            <Textarea
              label="Reason / Purpose of Leave"
              placeholder="State reason for leave application"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              rows={3}
            />

            <Group justify="flex-end" mt="lg">
              <Button variant="default" onClick={() => navigate("/leave")}>
                Cancel
              </Button>
              <Button type="submit" loading={applyMutation.isPending}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
