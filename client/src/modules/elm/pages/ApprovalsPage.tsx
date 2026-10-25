import { useState } from "react";
import {
  Button,
  Container,
  Group,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  usePendingApprovals,
  useSubstituteResponse,
  useTransitionLeave,
} from "../api/hooks";
import type { LeaveApplicationItem } from "../api/types";

export default function ApprovalsPage() {
  const approvalsQuery = usePendingApprovals();
  const transitionMutation = useTransitionLeave();
  const substituteMutation = useSubstituteResponse();

  const [activeApp, setActiveApp] = useState<LeaveApplicationItem | null>(null);
  const [actionType, setActionType] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");
  const [modalOpened, setModalOpened] = useState<boolean>(false);

  if (approvalsQuery.error) {
    return (
      <Container size="lg">
        <ErrorState error={approvalsQuery.error} />
      </Container>
    );
  }

  const openActionModal = (app: LeaveApplicationItem, action: string) => {
    setActiveApp(app);
    setActionType(action);
    setRemarks("");
    setModalOpened(true);
  };

  const handleConfirmAction = async () => {
    if (!activeApp) return;

    try {
      if (activeApp.status === "pending_substitute") {
        await substituteMutation.mutateAsync({
          id: activeApp.id,
          payload: {
            action: actionType as "accept" | "decline",
            remarks: remarks.trim(),
          },
        });
        notifications.show({
          color: "green",
          title: "Substitute Response Recorded",
          message: `You have successfully recorded your response as ${actionType}.`,
        });
      } else {
        await transitionMutation.mutateAsync({
          id: activeApp.id,
          payload: {
            action: actionType as "approve" | "reject" | "recommend" | "not_recommend",
            remarks: remarks.trim(),
          },
        });
        notifications.show({
          color: "green",
          title: "Action Recorded",
          message: `Decision '${actionType}' has been applied to application #${activeApp.id}.`,
        });
      }
      setModalOpened(false);
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Action Failed",
        message: errorMessage(err),
      });
    }
  };

  const pendingList = approvalsQuery.data ?? [];

  return (
    <Container size="lg" py="xl">
      <PageHeader
        title="Leave Approvals & Substitute Requests"
        subtitle="Review and act upon requests requiring your consent, recommendation, or sanction."
      />

      <Paper withBorder radius="md" mt="lg">
        {pendingList.length === 0 ? (
          <Text p="xl" ta="center" c="dimmed">
            No pending leave requests requiring your action.
          </Text>
        ) : (
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Applicant ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Current Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pendingList.map((app) => {
                const isSubstituteTask = app.status === "pending_substitute";
                const isUnitHeadReview = app.status === "submitted";
                const isSanctionReview = app.status === "pending_sanction";
                const isDirectSanctionCategory = ["CL", "RH"].includes(app.category_code);

                return (
                  <Table.Tr key={app.id}>
                    <Table.Td>#{app.id}</Table.Td>
                    <Table.Td>User #{app.user_id}</Table.Td>
                    <Table.Td fw={500}>
                      {app.category_name} ({app.category_code})
                    </Table.Td>
                    <Table.Td>
                      {app.start_date} to {app.end_date}
                    </Table.Td>
                    <Table.Td>{app.days_count}</Table.Td>
                    <Table.Td>
                      <StatusBadge status={app.status} />
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {isSubstituteTask && (
                          <>
                            <Button
                              size="xs"
                              color="green"
                              onClick={() => openActionModal(app, "accept")}
                            >
                              Accept
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => openActionModal(app, "decline")}
                            >
                              Decline
                            </Button>
                          </>
                        )}

                        {isUnitHeadReview && isDirectSanctionCategory && (
                          <>
                            <Button
                              size="xs"
                              color="green"
                              onClick={() => openActionModal(app, "approve")}
                            >
                              Approve
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => openActionModal(app, "reject")}
                            >
                              Reject
                            </Button>
                          </>
                        )}

                        {isUnitHeadReview && !isDirectSanctionCategory && (
                          <>
                            <Button
                              size="xs"
                              color="blue"
                              onClick={() => openActionModal(app, "recommend")}
                            >
                              Recommend
                            </Button>
                            <Button
                              size="xs"
                              color="orange"
                              variant="light"
                              onClick={() => openActionModal(app, "not_recommend")}
                            >
                              Not Recommend
                            </Button>
                          </>
                        )}

                        {isSanctionReview && (
                          <>
                            <Button
                              size="xs"
                              color="green"
                              onClick={() => openActionModal(app, "approve")}
                            >
                              Final Sanction
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => openActionModal(app, "reject")}
                            >
                              Reject
                            </Button>
                          </>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        )}
      </Paper>

      {/* Decision Modal */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title={`Confirm Action: ${actionType.replace("_", " ").toUpperCase()}`}
      >
        <Stack gap="md">
          <Text size="sm">
            You are about to record action <strong>{actionType}</strong> on leave
            request #{activeApp?.id} ({activeApp?.category_code}).
          </Text>
          <TextInput
            label="Remarks / Comments"
            placeholder="Add any remarks or notes for this decision..."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setModalOpened(false)}>
              Cancel
            </Button>
            <Button
              color={
                actionType.includes("reject") || actionType === "decline"
                  ? "red"
                  : "green"
              }
              loading={
                transitionMutation.isPending || substituteMutation.isPending
              }
              onClick={handleConfirmAction}
            >
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
