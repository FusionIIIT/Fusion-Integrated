import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Modal, Table, Text, Group, ActionIcon } from '@mantine/core';
import { IconCheck, IconX, IconEdit } from '@tabler/icons-react';
import { ApproveLeave, RejectLeave, LeaveRequest } from '../api/types/client';

const ApprovalsPage: React.FC = () => {
  const [opened, setOpened] = useState(false);
  const [selectedLeave, setSelectedLeave] = useState<LeaveRequest | null>(null);

  const fetchPendingLeaves = async () => {
    // Replace with actual API call
    return await fetch('/api/leaves/pending').then(res => res.json());
  };

  const { data: pendingLeaves, isLoading } = useQuery('pendingLeaves', fetchPendingLeaves);

  useEffect(() => {
    if (opened && selectedLeave) {
      // Fetch leave details for the selected leave
    }
  }, [opened, selectedLeave]);

  const handleApprove = async () => {
    if (selectedLeave) {
      await ApproveLeave(selectedLeave.id);
      setOpened(false);
      // Refetch pending leaves after approval
    }
  };

  const handleReject = async () => {
    if (selectedLeave) {
      await RejectLeave(selectedLeave.id);
      setOpened(false);
      // Refetch pending leaves after rejection
    }
  };

  return (
    <div>
      <Table withBorder captionSide="bottom">
        <thead>
          <tr>
            <th>Employee Name</th>
            <th>Start Date</th>
            <th>End Date</th>
            <th>Type</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td colSpan={6}>Loading...</td>
            </tr>
          ) : pendingLeaves && pendingLeaves.length > 0 ? (
            pendingLeaves.map(leave => (
              <tr key={leave.id}>
                <td>{leave.employee.name}</td>
                <td>{new Date(leave.startDate).toLocaleDateString()}</td>
                <td>{new Date(leave.endDate).toLocaleDateString()}</td>
                <td>{leave.type}</td>
                <td>{leave.status}</td>
                <td>
                  <Group spacing="xs">
                    <ActionIcon onClick={() => {}}>
                      <IconEdit />
                    </ActionIcon>
                    <ActionIcon color="green" onClick={() => setSelectedLeave(leave)}>
                      <IconCheck />
                    </ActionIcon>
                    <ActionIcon color="red" onClick={() => setSelectedLeave(leave)}>
                      <IconX />
                    </ActionIcon>
                  </Group>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6}>No pending leaves</td>
            </tr>
          )}
        </tbody>
      </Table>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Leave Action">
        {selectedLeave && (
          <>
            <Text size="sm">Employee: {selectedLeave.employee.name}</Text>
            <Text size="sm">Start Date: {new Date(selectedLeave.startDate).toLocaleDateString()}</Text>
            <Text size="sm">End Date: {new Date(selectedLeave.endDate).toLocaleDateString()}</Text>
            <Text size="sm">Type: {selectedLeave.type}</Text>
            <Group position="right" mt="md">
              <Button color="green" onClick={handleApprove}>
                Approve
              </Button>
              <Button color="red" onClick={handleReject}>
                Reject
              </Button>
            </Group>
          </>
        )}
      </Modal>
    </div>
  );
};

export default ApprovalsPage;