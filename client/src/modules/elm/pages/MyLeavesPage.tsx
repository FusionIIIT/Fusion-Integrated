import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeave, useCancelLeave, useMyLeaves } from "../api/hooks";
import type { ApplyLeavePayload, LeaveApplication } from "../api/types";

const LEAVE_TYPES = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
];

function getStatusBadge(status: string) {
  const colors: Record<string, string> = {
    PENDING: "yellow",
    APPROVED: "green",
    REJECTED: "red",
    CANCELLED: "gray",
  };
  return <Badge color={colors[status] ?? "gray"}>{status}</Badge>;
}

export default function MyLeavesPage() {
  const { data: leaves, isPending, error } = useMyLeaves();
  const applyMutation = useApplyLeave();
  const cancelMutation = useCancelLeave();

  const [modalOpened, setModalOpened] = useState(false);
  const [formData, setFormData] = useState<ApplyLeavePayload>({
    leave_type: "CL",
    start_date: "",
    end_date: "",
    reason: "",
    station_leave: false,
    substitute_user_id: null,
  });

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.start_date || !formData.end_date || !formData.reason) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Please fill in all required fields.",
      });
      return;
    }

    applyMutation.mutate(formData, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Success",
          message: "Leave application submitted successfully.",
        });
        setModalOpened(false);
        setFormData({
          leave_type: "CL",
          start_date: "",
          end_date: "",
          reason: "",
          station_leave: false,
          substitute_user_id: null,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Submission Failed",
          message: errorMessage(err),
        });
      },
    });
  }

  function handleCancel(id: number) {
    if (!window.confirm("Are you sure you want to cancel this leave application?")) return;
    cancelMutation.mutate(id, {
      onSuccess: () => {
        notifications.show({
          color: "gray",
          title: "Cancelled",
          message: "Leave application cancelled.",
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Cancellation Failed",
          message: errorMessage(err),
        });
      },
    });
  }

  return (
    <Container size="xl">
      <Group justify="space-between" mb="md">
        <PageHeader
          title="My Leaves"
          subtitle="View your leave applications and submit new leave requests"
        />
        <Button leftSection={<FaPlus />} onClick={() => setModalOpened(true)}>
          Apply for Leave
        </Button>
      </Group>

      <Card padding="lg" withBorder>
        {isPending ? (
          <Text c="dimmed">Loading applications...</Text>
        ) : !leaves?.length ? (
          <Text c="dimmed">No leave applications found.</Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Substitute</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {leaves.map((item: LeaveApplication) => (
                <Table.Tr key={item.id}>
                  <Table.Td>#{item.id}</Table.Td>
                  <Table.Td><Badge variant="outline">{item.leave_type}</Badge></Table.Td>
                  <Table.Td>{item.start_date} to {item.end_date}</Table.Td>
                  <Table.Td>{item.reason}</Table.Td>
                  <Table.Td>{item.substitute_name ?? "-"}</Table.Td>
                  <Table.Td>{getStatusBadge(item.status)}</Table.Td>
                  <Table.Td>
                    {item.status === "PENDING" && (
                      <ActionIcon
                        color="red"
                        variant="subtle"
                        title="Cancel Application"
                        onClick={() => handleCancel(item.id)}
                      >
                        <FaTimes />
                      </ActionIcon>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Apply for Leave"
        size="md"
      >
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Type"
              data={LEAVE_TYPES}
              value={formData.leave_type}
              onChange={(val) => setFormData((prev) => ({ ...prev, leave_type: val || "CL" }))}
              required
            />
            <TextInput
              label="Start Date"
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData((prev) => ({ ...prev, start_date: e.target.value }))}
              required
            />
            <TextInput
              label="End Date"
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData((prev) => ({ ...prev, end_date: e.target.value }))}
              required
            />
            <Textarea
              label="Reason"
              placeholder="State reason for leave"
              value={formData.reason}
              onChange={(e) => setFormData((prev) => ({ ...prev, reason: e.target.value }))}
              required
            />
            <TextInput
              label="Substitute User ID (Optional)"
              type="number"
              placeholder="e.g. 102"
              value={formData.substitute_user_id ?? ""}
              onChange={(e) => {
                const val = e.target.value ? parseInt(e.target.value, 10) : null;
                setFormData((prev) => ({ ...prev, substitute_user_id: val }));
              }}
            />
            <Checkbox
              label="Station Leave Required"
              checked={formData.station_leave}
              onChange={(e) => setFormData((prev) => ({ ...prev, station_leave: e.currentTarget.checked }))}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpened(false)}>Cancel</Button>
              <Button type="submit" loading={applyMutation.isPending}>Submit Application</Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Container>
  );
}

