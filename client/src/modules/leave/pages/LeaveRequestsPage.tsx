import { useState } from "react";
import {
  Button, Card, Checkbox, Container, Group, Modal, Select, Stack, Text,
  TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  type CreateLeaveRequest, type LeaveRequest, useCreateLeaveRequest,
  useLeaveRequests, useWithdrawLeaveRequest,
} from "../api/hooks";

const today = new Date().toISOString().slice(0, 10);

export default function LeaveRequestsPage() {
  const { data, isPending, error } = useLeaveRequests();
  const create = useCreateLeaveRequest();
  const withdraw = useWithdrawLeaveRequest();
  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState<CreateLeaveRequest>({
    category: "cl", starts_on: today, ends_on: today, cl_half: "full",
    reason: "", station_leave: false, station_leave_details: "",
  });

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const update = <K extends keyof CreateLeaveRequest>(key: K, value: CreateLeaveRequest[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  function submit() {
    create.mutate(form, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Leave request submitted",
          message: "Your request is now pending review." });
        setOpened(false);
      },
      onError: (e) => notifications.show({ color: "red", title: "Could not submit request",
        message: errorMessage(e) }),
    });
  }

  function cancel(request: LeaveRequest) {
    withdraw.mutate(request.id, {
      onSuccess: () => notifications.show({ color: "gray", title: "Request withdrawn",
        message: "The pending leave request was withdrawn." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not withdraw request",
        message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leave Requests"
        subtitle="Submit a CL or RH request and track its current status"
        action={<Button onClick={() => setOpened(true)}>Apply for Leave</Button>} />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={data?.results ?? []} loading={isPending} rowKey={(request) => request.id}
          minWidth={850}
          columns={[
            { key: "category", header: "Type", render: (request) =>
              request.category === "cl" ? "Casual Leave" : "Restricted Holiday" },
            { key: "period", header: "Period", render: (request) =>
              `${request.starts_on}${request.ends_on !== request.starts_on ? ` to ${request.ends_on}` : ""}` },
            { key: "half", header: "Day", render: (request) =>
              request.cl_half === "full" ? "Full day" : `${request.cl_half} half` },
            { key: "reason", header: "Reason", render: (request) => <Text lineClamp={2}>{request.reason}</Text> },
            { key: "status", header: "Status", render: (request) => <StatusBadge status={request.status} /> },
            { key: "actions", header: "", align: "right", render: (request) =>
              request.status === "pending" && <Button size="xs" variant="subtle" color="gray"
                loading={withdraw.isPending} onClick={() => cancel(request)}>Withdraw</Button> },
          ]}
          empty={{ icon: FaCalendarAlt, title: "No leave requests yet",
            description: "Leave requests you submit will appear here." }}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Apply for Leave" centered>
        <Stack>
          <Select label="Leave type" value={form.category} data={[
            { value: "cl", label: "Casual Leave" }, { value: "rh", label: "Restricted Holiday" },
          ]} onChange={(value) => update("category", (value ?? "cl") as "cl" | "rh")} />
          <Group grow>
            <TextInput label="Start date" type="date" value={form.starts_on}
              onChange={(event) => update("starts_on", event.currentTarget.value)} />
            <TextInput label="End date" type="date" value={form.ends_on}
              onChange={(event) => update("ends_on", event.currentTarget.value)} />
          </Group>
          {form.category === "cl" && <Select label="Duration" value={form.cl_half} data={[
            { value: "full", label: "Full day" }, { value: "first", label: "First half" },
            { value: "second", label: "Second half" },
          ]} onChange={(value) => update("cl_half", (value ?? "full") as CreateLeaveRequest["cl_half"])} />}
          <Textarea label="Reason" required value={form.reason}
            onChange={(event) => update("reason", event.currentTarget.value)} />
          <Checkbox label="I will be outside Jabalpur" checked={form.station_leave}
            onChange={(event) => update("station_leave", event.currentTarget.checked)} />
          {form.station_leave && <Textarea label="Station Leave details" required
            value={form.station_leave_details} onChange={(event) =>
              update("station_leave_details", event.currentTarget.value)} />}
          <Group justify="flex-end"><Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button loading={create.isPending} onClick={submit}>Submit request</Button></Group>
        </Stack>
      </Modal>
    </Container>
  );
}
