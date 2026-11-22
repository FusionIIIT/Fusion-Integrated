import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCancelLeave, useLeaves, useSubmitLeave } from "../api/hooks";
import type { StudentLeaveRequest } from "../api/types";

const LEAVE_TYPES = [
  { value: "CASUAL", label: "Casual Leave" },
  { value: "MEDICAL", label: "Medical Leave" },
  { value: "SHORT", label: "Short Leave" },
  { value: "SEMESTER_LEAVE", label: "Semester Leave of Absence" },
];

export default function StudentLeavePage() {
  const { data, isPending, error } = useLeaves();
  const { can, session } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  const [studentId, setStudentId] = useState(session?.user.username ?? "");
  const [studentName, setStudentName] = useState(session?.user.display_name ?? "");
  const [leaveType, setLeaveType] = useState("CASUAL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [documentUrl, setDocumentUrl] = useState("");

  const submitMutation = useSubmitLeave();
  const cancelMutation = useCancelLeave();

  const canApply = can("oap.leave.create");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading leave applications...</Text>
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const leaves = data?.results ?? [];

  const handleApply = async () => {
    try {
      await submitMutation.mutateAsync({
        student_id: studentId,
        student_name: studentName,
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        reason,
        document_url: documentUrl || undefined,
      });
      notifications.show({
        color: "green",
        title: "Application Submitted",
        message: "Your leave application has been submitted for review.",
      });
      setModalOpen(false);
      setReason("");
      setDocumentUrl("");
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Application Failed",
        message: errorMessage(e),
      });
    }
  };

  const handleCancel = async (req: StudentLeaveRequest) => {
    try {
      await cancelMutation.mutateAsync({ id: req.id, student_id: req.student_id });
      notifications.show({
        color: "green",
        title: "Leave Cancelled",
        message: "Your leave application has been successfully cancelled.",
      });
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Cancellation Failed",
        message: errorMessage(e),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Student Leave Applications"
        subtitle="Submit and track personal leaves of absence"
        action={
          canApply && (
            <Button onClick={() => setModalOpen(true)} data-testid="apply-leave-btn">
              Apply for Leave
            </Button>
          )
        }
      />

      {leaves.length === 0 ? (
        <Alert title="No leave applications" color="blue" data-testid="empty-state">
          You currently have no leave requests on record. Click &quot;Apply for Leave&quot; above to submit one.
        </Alert>
      ) : (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Duration</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {leaves.map((l) => (
                <Table.Tr key={l.id}>
                  <Table.Td fw={500}>#{l.id}</Table.Td>
                  <Table.Td>{l.leave_type}</Table.Td>
                  <Table.Td>
                    {l.start_date} to {l.end_date}
                  </Table.Td>
                  <Table.Td>{l.duration_days}</Table.Td>
                  <Table.Td>{l.reason}</Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        l.status === "APPROVED"
                          ? "green"
                          : l.status === "REJECTED"
                            ? "red"
                            : l.status === "CANCELLED"
                              ? "gray"
                              : "blue"
                      }
                      variant="light"
                    >
                      {l.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {l.status === "PENDING" && canApply && (
                      <Button
                        size="xs"
                        color="red"
                        variant="subtle"
                        loading={cancelMutation.isPending}
                        onClick={() => handleCancel(l)}
                        aria-label={`Cancel leave application #${l.id}`}
                      >
                        Cancel
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <FormModal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Apply for Student Leave"
        submitLabel="Submit Application"
        onSubmit={handleApply}
        submitting={submitMutation.isPending}
      >
        <Stack gap="md">
          <TextInput
            label="Student ID / Roll Number"
            value={studentId}
            onChange={(e) => setStudentId(e.currentTarget.value)}
            required
            aria-label="Student ID"
          />
          <TextInput
            label="Student Name"
            value={studentName}
            onChange={(e) => setStudentName(e.currentTarget.value)}
            required
            aria-label="Student Name"
          />
          <Select
            label="Leave Type"
            data={LEAVE_TYPES}
            value={leaveType}
            onChange={(val) => setLeaveType(val ?? "CASUAL")}
            required
            aria-label="Leave Type"
          />
          <Group grow>
            <TextInput
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
              required
              aria-label="Start Date"
            />
            <TextInput
              label="End Date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
              required
              aria-label="End Date"
            />
          </Group>
          <Textarea
            label="Reason for Leave"
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            required
            minRows={3}
            aria-label="Reason for Leave"
          />
          {leaveType === "MEDICAL" && (
            <TextInput
              label="Medical Certificate URL (Mandatory for medical leave > 3 days)"
              placeholder="https://storage.institution.edu/medical-certs/cert.pdf"
              value={documentUrl}
              onChange={(e) => setDocumentUrl(e.currentTarget.value)}
              aria-label="Medical Certificate URL"
            />
          )}
        </Stack>
      </FormModal>
    </Container>
  );
}
