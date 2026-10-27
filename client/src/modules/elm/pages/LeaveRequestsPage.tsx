import { useEffect, useState, type FormEvent } from "react";
import {
  Alert, Button, Card, Container, Group, Select, Stack, Table, Text,
  TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateLeaveRequest, useLeaveRequests, useWithdrawLeaveRequest,
} from "../api/hooks";
import type { LeaveCategory, LeaveRequestInput } from "../api/types";
import "./LeaveRequestsPage.css";

const categories: { value: LeaveCategory; label: string }[] = [
  { value: "CL", label: "Casual Leave" },
  { value: "RH", label: "Restricted Holiday" },
  { value: "SCL", label: "Special Casual Leave" },
  { value: "EL", label: "Earned Leave" },
  { value: "COL", label: "Commuted Leave" },
  { value: "VL", label: "Vacation Leave" },
];

const emptyRequest: LeaveRequestInput = {
  category: "CL",
  start_date: "",
  end_date: "",
  day_part: "full_day",
  reason: "",
};

export default function LeaveRequestsPage() {
  const requests = useLeaveRequests();
  const createRequest = useCreateLeaveRequest();
  const withdrawRequest = useWithdrawLeaveRequest();
  const [form, setForm] = useState(emptyRequest);
  const [printRequestId, setPrintRequestId] = useState<number | null>(null);
  const printRequest = requests.data?.results.find(
    (request) => request.id === printRequestId,
  );

  useEffect(() => {
    if (!printRequest) return;

    const clearPrintRequest = () => setPrintRequestId(null);
    window.addEventListener("afterprint", clearPrintRequest);
    window.print();
    return () => window.removeEventListener("afterprint", clearPrintRequest);
  }, [printRequest]);

  if (requests.error) {
    return <Container size="lg"><ErrorState error={requests.error} /></Container>;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const isSingleDayCasualLeave =
      form.category === "CL"
      && form.start_date !== ""
      && form.start_date === form.end_date;
    createRequest.mutate({
      ...form,
      day_part: isSingleDayCasualLeave ? form.day_part : "full_day",
    }, {
      onSuccess: () => {
        setForm(emptyRequest);
        notifications.show({
          color: "green", title: "Leave request submitted",
          message: "Your request is now pending review.",
        });
      },
      onError: (error) => notifications.show({
        color: "red", title: "Could not submit leave request",
        message: errorMessage(error),
      }),
    });
  }

  function withdraw(id: number) {
    withdrawRequest.mutate(id, {
      onSuccess: () => notifications.show({
        color: "green", title: "Request withdrawn",
        message: "The pending request has been withdrawn.",
      }),
      onError: (error) => notifications.show({
        color: "red", title: "Could not withdraw request",
        message: errorMessage(error),
      }),
    });
  }

  return (
    <Container size="lg">
      <PageHeader title="My Leave Requests" />
      <Card withBorder mb="lg">
        <form onSubmit={submit}>
          <Stack>
            <Select
              label="Leave category"
              data={categories}
              value={form.category}
              onChange={(value) => {
                const category = categories.find((item) => item.value === value);
                if (category) setForm({
                  ...form,
                  category: category.value,
                  day_part: "full_day",
                });
              }}
              required
            />
            <Group grow>
              <TextInput
                label="Start date"
                type="date"
                value={form.start_date}
                onChange={(event) =>
                  setForm({ ...form, start_date: event.currentTarget.value })}
                required
              />
              <TextInput
                label="End date"
                type="date"
                value={form.end_date}
                onChange={(event) =>
                  setForm({ ...form, end_date: event.currentTarget.value })}
                required
              />
            </Group>
            {form.category === "CL"
              && form.start_date !== ""
              && form.start_date === form.end_date && (
                <Select
                  label="Casual Leave period"
                  data={[
                    { value: "full_day", label: "Full day" },
                    { value: "first_half", label: "First half" },
                    { value: "second_half", label: "Second half" },
                  ]}
                  value={form.day_part}
                  onChange={(value) => {
                    if (value === "full_day"
                      || value === "first_half"
                      || value === "second_half") {
                      setForm({ ...form, day_part: value });
                    }
                  }}
                  required
                />
              )}
            <Textarea
              label="Purpose / reason"
              value={form.reason}
              onChange={(event) =>
                setForm({ ...form, reason: event.currentTarget.value })}
              minRows={2}
              required
            />
            <Group justify="flex-end">
              <Button type="submit" loading={createRequest.isPending}>
                Submit request
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>

      {requests.data?.results.length === 0 && (
        <Alert color="gray" mb="md">You have no leave requests yet.</Alert>
      )}
      {requests.data?.results.length ? (
        <Table.ScrollContainer minWidth={600}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.data.results.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>
                    {categories.find((category) => category.value === item.category)
                      ?.label ?? item.category}
                  </Table.Td>
                  <Table.Td>
                    {item.start_date} - {item.end_date}
                    {item.day_part !== "full_day"
                      ? ` (${item.day_part.replace("_", " ")})`
                      : ""}
                  </Table.Td>
                  <Table.Td>{item.reason}</Table.Td>
                  <Table.Td>
                    <Stack gap={2}>
                      <Text tt="capitalize">{item.status}</Text>
                      {item.events.map((event, index) => (
                        <Text key={`${event.event_type}-${index}`} size="xs" c="dimmed">
                          {event.event_type} - {new Date(event.created_at).toLocaleString()}
                        </Text>
                      ))}
                    </Stack>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      variant="subtle"
                      size="xs"
                      onClick={() => setPrintRequestId(item.id)}
                    >
                      Print
                    </Button>
                    {item.status === "pending" && (
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        loading={withdrawRequest.isPending}
                        onClick={() => withdraw(item.id)}
                      >
                        Withdraw
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      ) : null}
      {printRequest && (
        <article className="elm-print-sheet" aria-hidden="true">
          <h1>Employee Leave Application</h1>
          <p>Request number: {printRequest.id}</p>
          <dl>
            <dt>Employee ID</dt>
            <dd>{printRequest.user_id}</dd>
            <dt>Leave category</dt>
            <dd>
              {categories.find(
                (category) => category.value === printRequest.category,
              )?.label ?? printRequest.category}
            </dd>
            <dt>Period</dt>
            <dd>
              {printRequest.start_date} to {printRequest.end_date}
              {printRequest.day_part !== "full_day"
                ? ` (${printRequest.day_part.replace("_", " ")})`
                : ""}
            </dd>
            <dt>Purpose / reason</dt>
            <dd className="elm-print-reason">{printRequest.reason}</dd>
            <dt>Current status</dt>
            <dd>{printRequest.status}</dd>
            <dt>Submitted</dt>
            <dd>{new Date(printRequest.created_at).toLocaleString()}</dd>
          </dl>
          <h2>Recorded history</h2>
          <ol>
            {printRequest.events.map((event, index) => (
              <li key={`${event.event_type}-${index}`}>
                {event.event_type}: {event.from_status || "new"} to{" "}
                {event.to_status} — {new Date(event.created_at).toLocaleString()}
              </li>
            ))}
          </ol>
        </article>
      )}
    </Container>
  );
}
