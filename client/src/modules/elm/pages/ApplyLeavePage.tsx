import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
import { FaInfoCircle, FaPaperPlane } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeave, useMyBalances } from "../api/hooks";
import type { LeaveCategory } from "../api/types";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const applyMutation = useApplyLeave();
  const { data: balances } = useMyBalances();

  const [category, setCategory] = useState<LeaveCategory>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [half, setHalf] = useState<"full" | "first_half" | "second_half">("full");
  const [purpose, setPurpose] = useState<string>("");
  const [substituteId, setSubstituteId] = useState<number | string>("");
  const [stationLeaveRequired, setStationLeaveRequired] = useState<boolean>(false);
  const [stationLeaveAddress, setStationLeaveAddress] = useState<string>("");

  const needsSubstitute = ["SCL", "EL", "COL", "VL"].includes(category);
  const isContinuousCount = ["EL", "COL", "VL"].includes(category);

  // Find available balance for selected category
  const currentBalance = balances?.results?.find((b) => b.category === category);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!startDate || !endDate) {
      notifications.show({
        color: "red",
        title: "Required Fields",
        message: "Please specify both start date and end date.",
      });
      return;
    }

    applyMutation.mutate(
      {
        category,
        start_date: startDate,
        end_date: endDate,
        half,
        purpose,
        substitute_id: substituteId ? Number(substituteId) : null,
        station_leave_required: stationLeaveRequired,
        station_leave_address: stationLeaveAddress,
        submit: true,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "teal",
            title: "Leave Submitted",
            message: `Your ${data.category} request for ${data.days_counted} day(s) was submitted successfully.`,
          });
          navigate("/elm/my-leaves");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Submission Failed",
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
        subtitle="Submit a new leave application with automatic entitlement checks"
      />

      <Card padding="xl" radius="md" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="lg">
            {currentBalance !== undefined && (
              <Alert icon={<FaInfoCircle />} color="blue" variant="light">
                <Text size="sm">
                  Available <strong>{category}</strong> balance: <strong>{currentBalance.available} days</strong> (Credited: {currentBalance.credited}, Carried: {currentBalance.carried_forward}, Used: {currentBalance.used}).
                </Text>
              </Alert>
            )}

            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Leave Category"
                  description="Select policy category"
                  data={[
                    { value: "CL", label: "Casual Leave (CL)" },
                    { value: "RH", label: "Restricted Holiday (RH)" },
                    { value: "SCL", label: "Special Casual Leave (SCL)" },
                    { value: "EL", label: "Earned Leave (EL)" },
                    { value: "COL", label: "Commuted Leave (COL)" },
                    { value: "VL", label: "Vacation Leave (VL)" },
                  ]}
                  value={category}
                  onChange={(val) => setCategory((val as LeaveCategory) || "CL")}
                  required
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Half Day"
                  description="Applicable for CL"
                  data={[
                    { value: "full", label: "Full Day" },
                    { value: "first_half", label: "First Half (Morning)" },
                    { value: "second_half", label: "Second Half (Afternoon)" },
                  ]}
                  value={half}
                  onChange={(val) => setHalf((val as "full" | "first_half" | "second_half") || "full")}
                  disabled={category !== "CL"}
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="Start Date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="End Date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>

              {isContinuousCount && (
                <Grid.Col span={12}>
                  <Text size="xs" c="dimmed">
                    Note: For {category}, intervening weekends and closed holidays count towards the total chargeable leave days.
                  </Text>
                </Grid.Col>
              )}

              {needsSubstitute && (
                <Grid.Col span={12}>
                  <NumberInput
                    label="Nominated Substitute (User ID)"
                    description="Colleague taking responsibility for classes/official duties during absence"
                    placeholder="e.g. 102"
                    value={substituteId}
                    onChange={setSubstituteId}
                    min={1}
                    required
                  />
                </Grid.Col>
              )}

              <Grid.Col span={12}>
                <Checkbox
                  label="Station Leave Permission Required"
                  description="Check if you will be leaving the headquarters/station during this leave"
                  checked={stationLeaveRequired}
                  onChange={(e) => setStationLeaveRequired(e.currentTarget.checked)}
                />
              </Grid.Col>

              {stationLeaveRequired && (
                <Grid.Col span={12}>
                  <TextInput
                    label="Station Leave Contact Address & Phone"
                    placeholder="Address where you can be reached while out of station"
                    value={stationLeaveAddress}
                    onChange={(e) => setStationLeaveAddress(e.currentTarget.value)}
                    required={stationLeaveRequired}
                  />
                </Grid.Col>
              )}

              <Grid.Col span={12}>
                <Textarea
                  label="Purpose / Reason"
                  placeholder="State the reason for leave"
                  value={purpose}
                  onChange={(e) => setPurpose(e.currentTarget.value)}
                  minRows={3}
                />
              </Grid.Col>
            </Grid>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/elm/my-leaves")}>
                Cancel
              </Button>
              <Button
                type="submit"
                leftSection={<FaPaperPlane />}
                loading={applyMutation.isPending}
              >
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
