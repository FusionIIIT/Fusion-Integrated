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
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useInitiateNoDues, useNoDues } from "../api/hooks";

const REASONS = [
  { value: "GRADUATION", label: "Graduation / Convocation" },
  { value: "WITHDRAWAL", label: "Program Withdrawal" },
  { value: "MIGRATION", label: "Institute Migration / Transfer" },
];

export default function NoDuesPage() {
  const { data, isPending, error } = useNoDues();
  const { can, session } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const [reason, setReason] = useState("GRADUATION");

  const initiateMutation = useInitiateNoDues();
  const canInitiate = can("oap.nodues.initiate");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading institutional no-dues status...</Text>
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

  const requests = data?.results ?? [];
  const currentRequest = requests.length > 0 ? requests[0] : null;

  const handleInitiate = async () => {
    try {
      await initiateMutation.mutateAsync({
        student_id: session?.user.username ?? "STUDENT",
        reason,
      });
      notifications.show({
        color: "green",
        title: "No-Dues Initiated",
        message: "Institutional clearance workflows have been initiated across all departments.",
      });
      setModalOpen(false);
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Initiation Failed",
        message: errorMessage(e),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Institutional No-Dues Clearance"
        subtitle="Multi-departmental dues sign-off for graduation or departure"
        action={
          !currentRequest &&
          canInitiate && (
            <Button onClick={() => setModalOpen(true)} data-testid="initiate-nodues-btn">
              Initiate Clearance
            </Button>
          )
        }
      />

      {!currentRequest ? (
        <Alert title="No active clearance workflow" color="blue" data-testid="empty-state">
          You have not initiated a no-dues clearance request. Click &quot;Initiate Clearance&quot; above when preparing for graduation or departure.
        </Alert>
      ) : (
        <Stack gap="lg">
          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Overall Institutional Status
                </Text>
                <Title order={3} mt={4}>
                  {currentRequest.overall_status === "CLEARED"
                    ? "Fully Cleared"
                    : "Pending Departmental Sign-offs"}
                </Title>
                <Text size="sm" c="dimmed" mt={4}>
                  Reason: {currentRequest.reason.replace(/_/g, " ")} | Initiated on:{" "}
                  {new Date(currentRequest.created_at).toLocaleDateString()}
                </Text>
              </div>
              <Badge
                size="xl"
                color={
                  currentRequest.overall_status === "CLEARED"
                    ? "green"
                    : currentRequest.overall_status === "REJECTED"
                      ? "red"
                      : "orange"
                }
              >
                {currentRequest.overall_status}
              </Badge>
            </Group>

            {currentRequest.clearance_certificate_number && (
              <Alert color="green" mt="md" title="Clearance Certificate Issued">
                <Text size="sm">
                  Official Clearance Certificate #: <strong>{currentRequest.clearance_certificate_number}</strong>
                </Text>
              </Alert>
            )}
          </Card>

          <Card withBorder radius="md">
            <Title order={4} p="md">Departmental Sign-off Checklist</Title>
            <Table verticalSpacing="sm" striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Department / Section</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Outstanding Dues</Table.Th>
                  <Table.Th>Sign-off By</Table.Th>
                  <Table.Th>Remarks</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {currentRequest.signoffs.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td fw={500}>{s.department.replace(/_/g, " ")}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={
                          s.status === "CLEARED"
                            ? "green"
                            : s.status === "DUES_PENDING"
                              ? "red"
                              : "blue"
                        }
                        variant="light"
                      >
                        {s.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {parseFloat(s.dues_amount) > 0 ? (
                        <Text c="red" fw={600}>₹{s.dues_amount}</Text>
                      ) : (
                        "₹0.00"
                      )}
                    </Table.Td>
                    <Table.Td>{s.signoff_by || "Pending officer"}</Table.Td>
                    <Table.Td>{s.remarks || "—"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Stack>
      )}

      <FormModal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Initiate No-Dues Clearance"
        submitLabel="Initiate Process"
        onSubmit={handleInitiate}
        submitting={initiateMutation.isPending}
      >
        <Stack gap="md">
          <Select
            label="Reason for Clearance"
            data={REASONS}
            value={reason}
            onChange={(val) => setReason(val ?? "GRADUATION")}
            required
            aria-label="Reason for Clearance"
          />
          <Text size="xs" c="dimmed">
            Initiating will notify all 6 institutional departments (Library, Hostel, Accounts, Sports, Laboratories, Discipline) to verify and record clearance.
          </Text>
        </Stack>
      </FormModal>
    </Container>
  );
}
