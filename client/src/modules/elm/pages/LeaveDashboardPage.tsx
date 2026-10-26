import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCancelLeaveApplication,
  useExtendLeaveApplication,
  useLeaveApplications,
  useLeaveBalances,
  useReplaceSubstitute,
  useSubmitDutyResumption,
  useWithdrawLeaveApplication,
} from "../api/hooks";
import type { LeaveApplication, LeaveApplicationStatus } from "../api/types";

const STATUS_COLOR: Record<LeaveApplicationStatus, string> = {
  pending: "yellow",
  awaiting_substitute: "yellow",
  applicant_action_required: "orange",
  awaiting_unit_head: "blue",
  awaiting_final_sanction: "indigo",
  awaiting_director: "violet",
  recommended: "blue",
  approved: "green",
  rejected: "red",
  withdrawn: "gray",
  cancellation_pending_unit_head: "orange",
  cancellation_pending_final: "orange",
  cancelled: "gray",
};

export default function LeaveDashboardPage() {
  const balances = useLeaveBalances();
  const applications = useLeaveApplications();
  const withdraw = useWithdrawLeaveApplication();
  const cancel = useCancelLeaveApplication();
  const extend = useExtendLeaveApplication();
  const resume = useSubmitDutyResumption();
  const replaceSub = useReplaceSubstitute();

  // Modal states
  const [activeApp, setActiveApp] = useState<LeaveApplication | null>(null);
  const [modalType, setModalType] = useState<"cancel" | "extend" | "resume" | "substitute" | null>(
    null
  );
  const [inputVal1, setInputVal1] = useState("");
  const [inputVal2, setInputVal2] = useState("");

  const closeModal = () => {
    setActiveApp(null);
    setModalType(null);
    setInputVal1("");
    setInputVal2("");
  };

  const handleModalSubmit = () => {
    if (!activeApp) return;
    if (modalType === "cancel") {
      cancel.mutate({ id: activeApp.id, reason: inputVal1 }, { onSuccess: closeModal });
    } else if (modalType === "extend") {
      extend.mutate(
        {
          id: activeApp.id,
          start_date: inputVal1,
          end_date: inputVal2,
          reason: "Extension requested",
        },
        { onSuccess: closeModal }
      );
    } else if (modalType === "resume") {
      resume.mutate(
        { id: activeApp.id, actual_resumption_date: inputVal1, remarks: inputVal2 },
        { onSuccess: closeModal }
      );
    } else if (modalType === "substitute") {
      const subId = parseInt(inputVal1, 10);
      if (!Number.isNaN(subId)) {
        replaceSub.mutate(
          { id: activeApp.id, substitute_user_id: subId },
          { onSuccess: closeModal }
        );
      }
    }
  };

  if (balances.error) {
    return (
      <Container size="lg">
        <ErrorState error={balances.error} />
      </Container>
    );
  }
  if (applications.error) {
    return (
      <Container size="lg">
        <ErrorState error={applications.error} />
      </Container>
    );
  }

  const balanceList = balances.data?.results ?? [];
  const appList = applications.data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Leave Dashboard"
        subtitle="Your current leave balances and submitted applications"
      />
      <Stack gap="lg">
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
          {balanceList.map((b) => (
            <Card key={b.id} withBorder padding="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600}>{b.leave_type.name}</Text>
                <Badge variant="light">{b.leave_type.code}</Badge>
              </Group>
              <Text size="xl" fw={700}>
                {b.remaining} days remaining
              </Text>
              <Text size="xs" c="dimmed" mt="xs">
                Allocated: {b.allocated} | Used: {b.used} | Pending: {b.pending}
              </Text>
            </Card>
          ))}
        </SimpleGrid>

        <Card withBorder padding="lg">
          <Text fw={600} mb="md">
            My Leave Applications
          </Text>
          {appList.length === 0 ? (
            <Text size="sm" c="dimmed">
              No leave applications found.
            </Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {appList.map((app) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>
                      {app.leave_type.name}
                      {app.is_extension && <Badge size="xs" ml="xs">Extension</Badge>}
                      {app.is_offline && <Badge size="xs" color="gray" ml="xs">Offline</Badge>}
                    </Table.Td>
                    <Table.Td>
                      {app.start_date} to {app.end_date}
                    </Table.Td>
                    <Table.Td>{app.total_days}</Table.Td>
                    <Table.Td>
                      <Badge color={STATUS_COLOR[app.status] ?? "gray"} variant="light">
                        {app.status}
                      </Badge>
                      {app.cancellation_status && (
                        <Text size="xs" c="dimmed">
                          Cancel: {app.cancellation_status}
                        </Text>
                      )}
                      {app.resumption_status && (
                        <Text size="xs" c="dimmed">
                          Resumption: {app.resumption_status}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {["pending", "awaiting_substitute", "awaiting_unit_head"].includes(
                          app.status
                        ) && (
                          <Button
                            size="xs"
                            color="red"
                            variant="subtle"
                            loading={withdraw.isPending}
                            onClick={() => withdraw.mutate(app.id)}
                          >
                            Withdraw
                          </Button>
                        )}
                        {app.status === "applicant_action_required" && (
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            onClick={() => {
                              setActiveApp(app);
                              setModalType("substitute");
                            }}
                          >
                            Replace Substitute
                          </Button>
                        )}
                        {app.status === "approved" &&
                          !app.cancellation_status &&
                          !app.is_offline && (
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => {
                                setActiveApp(app);
                                setModalType("cancel");
                              }}
                            >
                              Cancel Leave
                            </Button>
                          )}
                        {app.status === "approved" &&
                          ["EL", "COL", "VL"].includes(app.leave_type.code) &&
                          !app.is_extension && (
                            <Button
                              size="xs"
                              color="blue"
                              variant="light"
                              onClick={() => {
                                setActiveApp(app);
                                setModalType("extend");
                              }}
                            >
                              Extend
                            </Button>
                          )}
                        {app.status === "approved" &&
                          ["EL", "COL", "VL"].includes(app.leave_type.code) &&
                          !app.resumption_status && (
                            <Button
                              size="xs"
                              color="teal"
                              variant="light"
                              onClick={() => {
                                setActiveApp(app);
                                setModalType("resume");
                              }}
                            >
                              Resume Duty
                            </Button>
                          )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>

      {/* Action Dialog Modal */}
      <Modal
        opened={modalType !== null}
        onClose={closeModal}
        title={
          modalType === "cancel"
            ? "Request Leave Cancellation"
            : modalType === "extend"
            ? "Apply for Leave Extension"
            : modalType === "resume"
            ? "Submit Duty Resumption"
            : "Nominate Replacement Substitute"
        }
      >
        <Stack gap="md">
          {modalType === "cancel" && (
            <TextInput
              label="Reason for cancellation"
              placeholder="Provide reason for cancellation"
              required
              value={inputVal1}
              onChange={(e) => setInputVal1(e.currentTarget.value)}
            />
          )}
          {modalType === "extend" && (
            <>
              <TextInput
                label="Extension Start Date (Contiguous day)"
                placeholder="YYYY-MM-DD"
                required
                value={inputVal1}
                onChange={(e) => setInputVal1(e.currentTarget.value)}
              />
              <TextInput
                label="Extension End Date"
                placeholder="YYYY-MM-DD"
                required
                value={inputVal2}
                onChange={(e) => setInputVal2(e.currentTarget.value)}
              />
            </>
          )}
          {modalType === "resume" && (
            <>
              <TextInput
                label="Actual Resumption Date"
                placeholder="YYYY-MM-DD"
                required
                value={inputVal1}
                onChange={(e) => setInputVal1(e.currentTarget.value)}
              />
              <TextInput
                label="Remarks"
                placeholder="Optional comments"
                value={inputVal2}
                onChange={(e) => setInputVal2(e.currentTarget.value)}
              />
            </>
          )}
          {modalType === "substitute" && (
            <TextInput
              label="Replacement Substitute User ID"
              placeholder="e.g. 104"
              required
              value={inputVal1}
              onChange={(e) => setInputVal1(e.currentTarget.value)}
            />
          )}
          <Group justify="flex-end" mt="md">
            <Button variant="subtle" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              onClick={handleModalSubmit}
              loading={
                cancel.isPending || extend.isPending || resume.isPending || replaceSub.isPending
              }
            >
              Submit
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
