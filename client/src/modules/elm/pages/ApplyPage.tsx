import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes, useSubmitLeaveApplication } from "../api";
import type { LeaveType } from "../types";

export default function ApplyPage() {
  const navigate = useNavigate();
  const { data: typesData, isPending: typesLoading, error: typesError } = useLeaveTypes();
  const submitMutation = useSubmitLeaveApplication();

  const [leaveTypeId, setLeaveTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  if (typesError) {
    return (
      <Container size="sm">
        <ErrorState error={typesError} />
      </Container>
    );
  }

  const leaveTypes = (typesData ?? []) as LeaveType[];

  const selectOptions = leaveTypes.map((t) => ({
    value: String(t.id),
    label: `${t.name} (${t.code})`,
  }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveTypeId) {
      notifications.show({
        color: "red",
        title: "Validation error",
        message: "Please select a leave type.",
      });
      return;
    }
    if (!startDate || !endDate) {
      notifications.show({
        color: "red",
        title: "Validation error",
        message: "Please choose both start and end dates.",
      });
      return;
    }
    if (endDate < startDate) {
      notifications.show({
        color: "red",
        title: "Validation error",
        message: "End date cannot precede start date.",
      });
      return;
    }

    submitMutation.mutate(
      {
        leave_type: Number(leaveTypeId),
        start_date: startDate,
        end_date: endDate,
        reason,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Application submitted",
            message: "Your leave application has been submitted successfully.",
          });
          navigate("/elm/applications");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Submission failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Container size="sm">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new leave application for approval"
      />
      <Card padding="lg" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Type"
              placeholder="Select leave type"
              data={selectOptions}
              value={leaveTypeId}
              onChange={setLeaveTypeId}
              disabled={typesLoading}
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
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </Group>
            <Textarea
              label="Reason"
              placeholder="Reason for requesting leave"
              rows={4}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                onClick={() => navigate("/elm/applications")}
              >
                Cancel
              </Button>
              <Button type="submit" loading={submitMutation.isPending}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
