import React, { useState, useEffect } from 'react';
import { Button, Card, Group, Text, Table, TextInput } from '@mantine/core';
import { IconPlus, IconRefresh, IconUser } from '@tabler/icons-react';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { fetchLeaveRequests, triggerYearEndProcessing, updateSLAStatus } from '../api/leaveActions';
import { LeaveRequest, SLAStatus } from '../types/client';

const AdminPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const leaveRequests = useAppSelector(state => state.leave.requests);
  const slaStatus = useAppSelector(state => state.leave.slaStatus);

  useEffect(() => {
    dispatch(fetchLeaveRequests());
  }, [dispatch]);

  const handleYearEndProcessing = async () => {
    await dispatch(triggerYearEndProcessing());
  };

  const handleSLAUpdate = async (requestId: string, status: SLAStatus) => {
    await dispatch(updateSLAStatus(requestId, status));
  };

  return (
    <Card>
      <Group position="apart" mb="md">
        <Text size="lg">Employee Leave Management</Text>
        <Button onClick={handleYearEndProcessing} leftIcon={<IconRefresh />}>
          Trigger Year-End Processing
        </Button>
      </Group>

      <Table striped highlightOnHover>
        <thead>
          <tr>
            <th>Employee ID</th>
            <th>Start Date</th>
            <th>End Date</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {leaveRequests.map(request => (
            <tr key={request.id}>
              <td>{request.employeeId}</td>
              <td>{request.startDate.toDateString()}</td>
              <td>{request.endDate.toDateString()}</td>
              <td>{request.status}</td>
              <td>
                <Group spacing="xs">
                  <Button
                    color="green"
                    onClick={() => handleSLAUpdate(request.id, 'Completed')}
                    disabled={request.status === 'Completed'}
                  >
                    Mark as Completed
                  </Button>
                  <Button
                    color="red"
                    onClick={() => handleSLAUpdate(request.id, 'Pending')}
                    disabled={request.status === 'Pending'}
                  >
                    Mark as Pending
                  </Button>
                </Group>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Card.Section mt="md">
        <Text size="lg">SLA Status</Text>
        <TextInput
          label="Enter SLA Status"
          value={slaStatus}
          onChange={(e) => dispatch(updateSLAStatus('', e.target.value as SLAStatus))}
          rightSection={<IconUser />}
        />
      </Card.Section>
    </Card>
  );
};

export default AdminPage;