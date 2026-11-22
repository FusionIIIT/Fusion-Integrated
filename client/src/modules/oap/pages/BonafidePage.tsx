import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
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
import { useBonafides, useSubmitBonafide } from "../api/hooks";

const PURPOSES = [
  { value: "GENERAL", label: "General Verification" },
  { value: "PASSPORT", label: "Passport Application" },
  { value: "VISA", label: "Visa Application" },
  { value: "BANK_LOAN", label: "Education / Bank Loan" },
  { value: "INTERNSHIP", label: "Internship / External Project" },
];

export default function BonafidePage() {
  const { data, isPending, error } = useBonafides();
  const { can, session } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  const [studentId, setStudentId] = useState(session?.user.username ?? "");
  const [purpose, setPurpose] = useState("GENERAL");
  const [details, setDetails] = useState("");

  const submitMutation = useSubmitBonafide();
  const canApply = can("oap.bonafide.create");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Stack align="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading bonafide certificate requests...</Text>
        </Stack>
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

  const handleApply = async () => {
    try {
      await submitMutation.mutateAsync({
        student_id: studentId,
        purpose,
        details: details || undefined,
      });
      notifications.show({
        color: "green",
        title: "Request Submitted",
        message: "Your bonafide certificate request has been submitted to Academic Administration.",
      });
      setModalOpen(false);
      setDetails("");
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Submission Failed",
        message: errorMessage(e),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Bonafide Certificates"
        subtitle="Request official bonafide certificates and download authenticated documents"
        action={
          canApply && (
            <Button onClick={() => setModalOpen(true)} data-testid="apply-bonafide-btn">
              Request Certificate
            </Button>
          )
        }
      />

      {requests.length === 0 ? (
        <Alert title="No bonafide requests" color="blue" data-testid="empty-state">
          You have not applied for any bonafide certificates. Click &quot;Request Certificate&quot; to apply.
        </Alert>
      ) : (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Purpose</Table.Th>
                <Table.Th>Details</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Certificate #</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td fw={500}>#{r.id}</Table.Td>
                  <Table.Td>{r.purpose.replace(/_/g, " ")}</Table.Td>
                  <Table.Td>{r.details || "—"}</Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        r.status === "APPROVED"
                          ? "green"
                          : r.status === "REJECTED"
                            ? "red"
                            : "blue"
                      }
                      variant="light"
                    >
                      {r.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{r.certificate_number || "Pending issuance"}</Table.Td>
                  <Table.Td>
                    {r.status === "APPROVED" && (
                      <Button
                        size="xs"
                        variant="light"
                        component="a"
                        href={`/api/v1/oap/bonafide/${r.id}/download/`}
                        target="_blank"
                        rel="noreferrer"
                        aria-label={`Download certificate #${r.certificate_number ?? r.id}`}
                      >
                        Download PDF
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
        title="Request Bonafide Certificate"
        submitLabel="Submit Request"
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
          <Select
            label="Purpose of Certificate"
            data={PURPOSES}
            value={purpose}
            onChange={(val) => setPurpose(val ?? "GENERAL")}
            required
            aria-label="Purpose of Certificate"
          />
          <Textarea
            label="Specific Details or Addressee"
            placeholder="e.g. Addressed to Regional Passport Office, Bhopal"
            value={details}
            onChange={(e) => setDetails(e.currentTarget.value)}
            minRows={3}
            aria-label="Specific Details"
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
