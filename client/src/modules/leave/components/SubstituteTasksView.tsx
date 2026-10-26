import {
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useRespondSubstitute, useSubstituteTasks } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export function SubstituteTasksView() {
  const { data: tasks, isPending } = useSubstituteTasks();
  const respondMutation = useRespondSubstitute();

  const [activeTask, setActiveTask] = useState<LeaveApplication | null>(null);
  const [isAcceptAction, setIsAcceptAction] = useState<boolean>(true);
  const [remarks, setRemarks] = useState<string>("");

  const handleAction = async () => {
    if (!activeTask) return;
    try {
      await respondMutation.mutateAsync({
        id: activeTask.id,
        accept: isAcceptAction,
        remarks,
      });
      notifications.show({
        title: isAcceptAction ? "Responsibility Accepted" : "Responsibility Declined",
        message: `Updated substitute status for Leave #${activeTask.id}.`,
        color: isAcceptAction ? "green" : "orange",
      });
      setActiveTask(null);
      setRemarks("");
    } catch (e) {
      notifications.show({ title: "Action Failed", message: errorMessage(e), color: "red" });
    }
  };

  return (
    <Stack gap="md">
      <Card withBorder padding="md" radius="md">
        <Title order={4} mb="md">Pending Substitute Responsibility Requests</Title>
        {isPending ? (
          <Center py="xl"><Loader size="md" /></Center>
        ) : !tasks || tasks.length === 0 ? (
          <Center py="xl"><Text c="dimmed">No pending substitute tasks.</Text></Center>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Application</Table.Th>
                <Table.Th>Applicant</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tasks.map((task) => (
                <Table.Tr key={task.id}>
                  <Table.Td>#{task.id}</Table.Td>
                  <Table.Td>User #{task.applicant_user_id}</Table.Td>
                  <Table.Td><Badge>{task.leave_type}</Badge></Table.Td>
                  <Table.Td>{task.start_date} → {task.end_date}</Table.Td>
                  <Table.Td>{task.reason}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        leftSection={<FaCheck size={12} />}
                        onClick={() => {
                          setActiveTask(task);
                          setIsAcceptAction(true);
                          setRemarks("");
                        }}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<FaTimes size={12} />}
                        onClick={() => {
                          setActiveTask(task);
                          setIsAcceptAction(false);
                          setRemarks("");
                        }}
                      >
                        Decline
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal
        opened={!!activeTask}
        onClose={() => setActiveTask(null)}
        title={isAcceptAction ? "Accept Substitute Responsibility" : "Decline Substitute Responsibility"}
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            {isAcceptAction
              ? `Confirm acceptance of responsibility for User #${activeTask?.applicant_user_id}'s leave period (${activeTask?.start_date} to ${activeTask?.end_date}).`
              : `Confirm declining substitute coverage for Leave #${activeTask?.id}.`}
          </Text>
          <Textarea
            label="Remarks (optional)"
            placeholder="Add any relevant notes..."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActiveTask(null)}>Cancel</Button>
            <Button
              color={isAcceptAction ? "green" : "red"}
              onClick={handleAction}
              loading={respondMutation.isPending}
            >
              {isAcceptAction ? "Confirm Accept" : "Confirm Decline"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
