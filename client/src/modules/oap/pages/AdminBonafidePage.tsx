import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
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
import {
  useApproveBonafide,
  useBonafides,
  useRejectBonafide,
} from "../api/hooks";
import type { BonafideRequest } from "../api/types";

export default function AdminBonafidePage() {
  const { data, isPending, error } = useBonafides();
  const { can, session } = useAuth();

  const [activeReq, setActiveReq] = useState<BonafideRequest | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [remarks, setRemarks] = useState("");
  const [adminId, setAdminId] = useState(session?.user.username ?? "ACADEMIC_ADMIN");

  const approveMutation = useApproveBonafide();
  const rejectMutation = useRejectBonafide();

  const canIssue = can("oap.bonafide.issue");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading pending bonafide applications...</Text>
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

  const allReqs = data?.results ?? [];
  const pendingReqs = allReqs.filter((r) => r.status === "PENDING");

  const handleAction = async () => {
    if (!activeReq) return;
    try {
      if (actionType === "approve") {
        const res = await approveMutation.mutateAsync({
          id: activeReq.id,
          issued_by: adminId,
          remarks: remarks || "Verified and issued by Academic Administration.",
        });
        notifications.show({
          color: "green",
          title: "Certificate Issued",
          message: `Bonafide Certificate #${res.certificate_number} has been generated.`,
        });
      } else {
        await rejectMutation.mutateAsync({
          id: activeReq.id,
          issued_by: adminId,
          reason: remarks || "Did not satisfy documentation verification requirements.",
        });
        notifications.show({
          color: "red",
          title: "Request Rejected",
          message: `Bonafide request #${activeReq.id} has been rejected.`,
        });
      }
      setActiveReq(null);
      setRemarks("");
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Action Failed",
        message: errorMessage(e),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Bonafide Certificate Administration"
        subtitle="Verify academic eligibility and issue official certificates"
      />

      {pendingReqs.length === 0 ? (
        <Alert title="No Pending Requests" color="blue" data-testid="empty-state">
          All bonafide certificate requests have been verified and processed.
        </Alert>
      ) : (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Student ID</Table.Th>
                <Table.Th>Purpose</Table.Th>
                <Table.Th>Details</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pendingReqs.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td fw={500}>#{r.id}</Table.Td>
                  <Table.Td>{r.student_id}</Table.Td>
                  <Table.Td>{r.purpose.replace(/_/g, " ")}</Table.Td>
                  <Table.Td>{r.details || "—"}</Table.Td>
                  <Table.Td>
                    <Badge color="blue" variant="light">
                      {r.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {canIssue && (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => {
                            setActiveReq(r);
                            setActionType("approve");
                          }}
                          aria-label={`Approve and issue bonafide #${r.id}`}
                        >
                          Approve & Issue
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => {
                            setActiveReq(r);
                            setActionType("reject");
                          }}
                          aria-label={`Reject bonafide #${r.id}`}
                        >
                          Reject
                        </Button>
                      </Group>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <FormModal
        opened={activeReq !== null}
        onClose={() => setActiveReq(null)}
        title={
          actionType === "approve"
            ? `Approve & Issue Bonafide Certificate #${activeReq?.id}`
            : `Reject Bonafide Request #${activeReq?.id}`
        }
        submitLabel={actionType === "approve" ? "Issue Certificate" : "Confirm Rejection"}
        onSubmit={handleAction}
        submitting={approveMutation.isPending || rejectMutation.isPending}
      >
        <Stack gap="md">
          <TextInput
            label="Issuing Officer ID"
            value={adminId}
            onChange={(e) => setAdminId(e.currentTarget.value)}
            required
            aria-label="Issuing Officer ID"
          />
          <Textarea
            label={actionType === "approve" ? "Remarks / Certificate Endorsement" : "Rejection Reason"}
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
            required={actionType === "reject"}
            minRows={3}
            aria-label="Remarks or Rejection Reason"
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
