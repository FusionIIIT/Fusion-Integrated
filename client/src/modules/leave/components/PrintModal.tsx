import {
  Button,
  Divider,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import React from "react";
import type { LeaveRequest } from "../types";

interface PrintModalProps {
  opened: boolean;
  onClose: () => void;
  leave: LeaveRequest | null;
}

export const PrintModal: React.FC<PrintModalProps> = ({ opened, onClose, leave }) => {
  if (!leave) return null;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="lg"
      title={<Title order={4}>Leave Application Record</Title>}
    >
      <Stack gap="md" id="printable-leave-record">
        <Group justify="space-between">
          <div>
            <Text fw={700} size="lg">
              Fusion ERP • Employee Leave Management
            </Text>
            <Text size="xs" c="dimmed">
              Indian Institute of Information Technology, Design and Manufacturing
              Jabalpur
            </Text>
          </div>
          <Button size="xs" variant="outline" onClick={() => window.print()}>
            Print / Save PDF
          </Button>
        </Group>

        <Divider />

        <Table withTableBorder withColumnBorders>
          <Table.Tbody>
            <Table.Tr>
              <Table.Td fw={600} w={180}>Application ID</Table.Td>
              <Table.Td>#{leave.id}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td fw={600}>Applicant Employee ID</Table.Td>
              <Table.Td>User #{leave.user_id}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td fw={600}>Leave Category</Table.Td>
              <Table.Td>{leave.category}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td fw={600}>Leave Duration</Table.Td>
              <Table.Td>
                {leave.start_date} to {leave.end_date} ({leave.computed_days} day(s))
                {leave.half_day !== "NONE" && ` [${leave.half_day}]`}
              </Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td fw={600}>Reason</Table.Td>
              <Table.Td>{leave.reason}</Table.Td>
            </Table.Tr>
            <Table.Tr>
              <Table.Td fw={600}>Current Status</Table.Td>
              <Table.Td>{leave.status}</Table.Td>
            </Table.Tr>
            {leave.station_leave && (
              <Table.Tr>
                <Table.Td fw={600}>Station Leave</Table.Td>
                <Table.Td>
                  Address: {leave.station_address || "N/A"} | Contact:{" "}
                  {leave.station_contact || "N/A"}
                </Table.Td>
              </Table.Tr>
            )}
            {leave.substitute_user_id && (
              <Table.Tr>
                <Table.Td fw={600}>Substitute Employee</Table.Td>
                <Table.Td>
                  User #{leave.substitute_user_id} (Status: {leave.substitute_status})
                </Table.Td>
              </Table.Tr>
            )}
            {leave.unit_head_recommendation && (
              <Table.Tr>
                <Table.Td fw={600}>Unit Head Review</Table.Td>
                <Table.Td>
                  {leave.unit_head_recommendation}: {leave.unit_head_remarks || "No remarks"}
                </Table.Td>
              </Table.Tr>
            )}
            {leave.sanction_remarks && (
              <Table.Tr>
                <Table.Td fw={600}>Sanction Remarks</Table.Td>
                <Table.Td>{leave.sanction_remarks}</Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>

        {leave.action_logs && leave.action_logs.length > 0 && (
          <div>
            <Text fw={600} mb="xs">
              Workflow Transition History
            </Text>
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Time</Table.Th>
                  <Table.Th>Action</Table.Th>
                  <Table.Th>By (User)</Table.Th>
                  <Table.Th>Remarks</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {leave.action_logs.map((log) => (
                  <Table.Tr key={log.id}>
                    <Table.Td size="xs">{new Date(log.created_at).toLocaleString()}</Table.Td>
                    <Table.Td>{log.action}</Table.Td>
                    <Table.Td>#{log.actor_user_id}</Table.Td>
                    <Table.Td>{log.remarks || "-"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </div>
        )}
      </Stack>
    </Modal>
  );
};
