import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaCheckCircle, FaExclamationCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useSpecialFoodRequests, useSubmitSpecialFoodRequest } from "../api/hooks";

export default function SpecialFoodRequestPage() {
  const { data: requests, isLoading, error } = useSpecialFoodRequests();
  const submitRequest = useSubmitSpecialFoodRequest();

  const [reason, setReason] = useState("");
  const [requestedDate, setRequestedDate] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || !requestedDate) {
      notifications.show({
        color: "red",
        title: "Validation error",
        message: "Please provide both reason and requested date.",
      });
      return;
    }

    submitRequest.mutate(
      { reason: reason.trim(), requested_date: requestedDate },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Request Submitted",
            message: "Your special food request has been submitted for caretaker review.",
          });
          setReason("");
          setRequestedDate("");
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
  };

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="md">
      <PageHeader title="Special Food Request" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              <Text fw={600}>Submit Special Food Request</Text>
              <Text size="sm" c="dimmed">
                Requests must be submitted at least one calendar day in advance.
              </Text>
              <TextInput
                label="Requested Date"
                type="date"
                required
                value={requestedDate}
                onChange={(e) => setRequestedDate(e.currentTarget.value)}
              />
              <TextInput
                label="Reason"
                placeholder="e.g. Medical dietary need, fasting, festival"
                required
                value={reason}
                onChange={(e) => setReason(e.currentTarget.value)}
              />
              <Group justify="flex-end">
                <Button type="submit" loading={submitRequest.isPending}>
                  Submit Request
                </Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">
            My Special Food Requests
          </Text>
          {isLoading ? (
            <Text c="dimmed">Loading requests...</Text>
          ) : !requests || requests.length === 0 ? (
            <Alert color="gray" icon={<FaCalendarAlt />}>
              You have not submitted any special food requests.
            </Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Requested Date</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Decision Note</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {requests.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.requested_date}</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>
                      <StatusBadge status={r.status} />
                    </Table.Td>
                    <Table.Td>{r.decision_note || "—"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
