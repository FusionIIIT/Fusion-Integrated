import { useState, type FormEvent } from "react";
import {
  Alert, Button, Card, Container, Select, Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateLeaveApplication, useLeaveTypes } from "../api/hooks";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const leaveTypes = useLeaveTypes();
  const createLeave = useCreateLeaveApplication();
  const [leaveType, setLeaveType] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  if (leaveTypes.error) {
    return <Container size="md"><ErrorState error={leaveTypes.error} /></Container>;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!leaveType) {
      notifications.show({ color: "red", title: "Choose a leave type",
        message: "Select the category for your leave request." });
      return;
    }
    if (endDate < startDate) {
      notifications.show({ color: "red", title: "Check the dates",
        message: "End date cannot be before start date." });
      return;
    }
    createLeave.mutate({
      leave_type: leaveType,
      start_date: startDate,
      end_date: endDate,
      reason: reason.trim(),
    }, {
      onSuccess: (application) => {
        notifications.show({
          color: "green",
          title: "Leave request submitted",
          message: `Request #${application.id} has been saved with Pending status.`,
        });
        navigate("/apply_leave/my-leaves");
      },
      onError: (error) => notifications.show({
        color: "red", title: "Could not submit leave", message: errorMessage(error),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply Leave"
        subtitle="Submit a full-day leave request and track it under My Leaves"
      />
      <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
        <Text size="sm">
          This MVP saves requests as Pending. Approval routing, leave-balance checks,
          holiday-calendar validation, and half-day requests are not available yet.
          Overlapping pending or approved full-day requests are rejected.
        </Text>
      </Alert>
      <Card padding="lg" withBorder>
        <form onSubmit={submit}>
          <Stack gap="md">
            <Select
              label="Leave type"
              placeholder={leaveTypes.isPending ? "Loading leave types…" : "Select a category"}
              data={(leaveTypes.data?.results ?? []).map((item) => ({
                value: item.code, label: `${item.code} — ${item.label}`,
              }))}
              value={leaveType}
              onChange={setLeaveType}
              required
              searchable
              nothingFoundMessage="No leave types available"
              disabled={leaveTypes.isPending || !(leaveTypes.data?.results.length)}
            />
            <TextInput
              label="Start date"
              type="date"
              value={startDate}
              onChange={(event) => {
                setStartDate(event.currentTarget.value);
                if (endDate && event.currentTarget.value && endDate < event.currentTarget.value) {
                  setEndDate(event.currentTarget.value);
                }
              }}
              required
            />
            <TextInput
              label="End date"
              type="date"
              value={endDate}
              min={startDate || undefined}
              onChange={(event) => setEndDate(event.currentTarget.value)}
              required
            />
            <Textarea
              label="Reason / purpose"
              placeholder="Briefly explain why you are requesting leave"
              value={reason}
              onChange={(event) => setReason(event.currentTarget.value)}
              minRows={3}
              maxLength={2000}
              required
            />
            <Button
              type="submit"
              loading={createLeave.isPending}
              disabled={leaveTypes.isPending || !leaveTypes.data?.results.length}
            >
              Submit leave request
            </Button>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
