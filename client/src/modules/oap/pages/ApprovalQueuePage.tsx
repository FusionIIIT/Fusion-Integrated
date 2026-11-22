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
  useApproveLeave,
  useLeaves,
  useRecommendLeave,
  useRejectLeave,
} from "../api/hooks";
import type { StudentLeaveRequest } from "../api/types";

export default function ApprovalQueuePage() {
  const { data, isPending, error } = useLeaves();
  const { can, session } = useAuth();

  const [activeLeave, setActiveLeave] = useState<StudentLeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"recommend" | "approve" | "reject">("approve");
  const [remarks, setRemarks] = useState("");
  const [approverId, setApproverId] = useState(session?.user.username ?? "OFFICER");

  const recommendMutation = useRecommendLeave();
  const approveMutation = useApproveLeave();
  const rejectMutation = useRejectLeave();

  const canRecommend = can("oap.leave.recommend");
  const canApprove = can("oap.leave.approve");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading institutional approval queue...</Text>
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

  const allLeaves = data?.results ?? [];
  const pendingLeaves = allLeaves.filter(
    (l) => l.status === "PENDING" || l.status === "RECOMMENDED"
  );

  const handleAction = async () => {
    if (!activeLeave) return;
    try {
      if (actionType === "recommend") {
        await recommendMutation.mutateAsync({
          id: activeLeave.id,
          supervisor_id: approverId,
          remarks,
        });
        notifications.show({
          color: "green",
          title: "Leave Recommended",
          message: `Leave #${activeLeave.id} has been recommended.`,
        });
      } else if (actionType === "approve") {
        await approveMutation.mutateAsync({
          id: activeLeave.id,
          hod_id: approverId,
          remarks: remarks || "Approved by HoD.",
        });
        notifications.show({
          color: "green",
          title: "Leave Approved",
          message: `Leave #${activeLeave.id} has been sanctioned.`,
        });
      } else if (actionType === "reject") {
        await rejectMutation.mutateAsync({
          id: activeLeave.id,
          hod_id: approverId,
          remarks: remarks || "Disapproved by HoD.",
        });
        notifications.show({
          color: "red",
          title: "Leave Rejected",
          message: `Leave #${activeLeave.id} has been rejected.`,
        });
      }
      setActiveLeave(null);
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
        title="Leave Approval Queue"
        subtitle="Review and process student leave applications requiring faculty or departmental sanction"
      />

      {pendingLeaves.length === 0 ? (
        <Alert title="Queue Empty" color="blue" data-testid="empty-state">
          There are no pending leave applications awaiting approval at this time.
        </Alert>
      ) : (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Student</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Duration</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Current Status</Table.Th>
                <Table.Th>Decision Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pendingLeaves.map((l) => (
                <Table.Tr key={l.id}>
                  <Table.Td fw={500}>#{l.id}</Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={500}>{l.student_name}</Text>
                    <Text size="xs" c="dimmed">{l.student_id}</Text>
                  </Table.Td>
                  <Table.Td>{l.leave_type}</Table.Td>
                  <Table.Td>
                    {l.start_date} to {l.end_date} ({l.duration_days}d)
                  </Table.Td>
                  <Table.Td>{l.reason}</Table.Td>
                  <Table.Td>
                    <Badge color={l.status === "RECOMMENDED" ? "cyan" : "blue"} variant="light">
                      {l.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {canRecommend && l.status === "PENDING" && (
                        <Button
                          size="xs"
                          variant="light"
                          color="cyan"
                          onClick={() => {
                            setActiveLeave(l);
                            setActionType("recommend");
                          }}
                          aria-label={`Recommend leave #${l.id}`}
                        >
                          Recommend
                        </Button>
                      )}
                      {canApprove && (
                        <>
                          <Button
                            size="xs"
                            color="green"
                            onClick={() => {
                              setActiveLeave(l);
                              setActionType("approve");
                            }}
                            aria-label={`Approve leave #${l.id}`}
                          >
                            Approve
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            onClick={() => {
                              setActiveLeave(l);
                              setActionType("reject");
                            }}
                            aria-label={`Reject leave #${l.id}`}
                          >
                            Reject
                          </Button>
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <FormModal
        opened={activeLeave !== null}
        onClose={() => setActiveLeave(null)}
        title={
          actionType === "recommend"
            ? `Recommend Leave #${activeLeave?.id}`
            : actionType === "approve"
              ? `Approve Leave #${activeLeave?.id}`
              : `Reject Leave #${activeLeave?.id}`
        }
        submitLabel={
          actionType === "recommend"
            ? "Submit Recommendation"
            : actionType === "approve"
              ? "Confirm Approval"
              : "Confirm Rejection"
        }
        onSubmit={handleAction}
        submitting={
          recommendMutation.isPending ||
          approveMutation.isPending ||
          rejectMutation.isPending
        }
      >
        <Stack gap="md">
          <TextInput
            label="Approver / Officer ID"
            value={approverId}
            onChange={(e) => setApproverId(e.currentTarget.value)}
            required
            aria-label="Approver ID"
          />
          <Textarea
            label="Remarks / Decision Rationale"
            placeholder="Enter any comments, terms, or reasons"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
            required={actionType === "reject"}
            minRows={3}
            aria-label="Remarks"
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
