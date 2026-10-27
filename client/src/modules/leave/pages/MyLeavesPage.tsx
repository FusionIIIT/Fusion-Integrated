import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Table, Text, Badge, Group } from '@mantine/core';
import { IconArrowLeft, IconCheck, IconX, IconClockwise } from '@tabler/icons-react';
import { LeaveRequest, LeaveStatus } from '../api/types';

const MyLeavesPage: React.FC = () => {
  const navigate = useNavigate();
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);

  useEffect(() => {
    // Fetch user's leave requests
    fetch('/api/leave/my-leaves/')
      .then(response => response.json())
      .then(data => setLeaves(data))
      .catch(error => console.error('Error fetching leaves:', error));
  }, []);

  const handleWithdraw = (id: number) => {
    // Logic to withdraw a leave request
    fetch(`/api/leave/${id}/withdraw/`, { method: 'POST' })
      .then(response => response.json())
      .then(data => {
        setLeaves(leaves.map(leave => (leave.id === id ? data : leave)));
      })
      .catch(error => console.error('Error withdrawing leave:', error));
  };

  const handleCancel = (id: number) => {
    // Logic to cancel a leave request
    fetch(`/api/leave/${id}/cancel/`, { method: 'POST' })
      .then(response => response.json())
      .then(data => {
        setLeaves(leaves.map(leave => (leave.id === id ? data : leave)));
      })
      .catch(error => console.error('Error canceling leave:', error));
  };

  const handleResumption = (id: number) => {
    // Logic to resume a leave request
    fetch(`/api/leave/${id}/resume/`, { method: 'POST' })
      .then(response => response.json())
      .then(data => {
        setLeaves(leaves.map(leave => (leave.id === id ? data : leave)));
      })
      .catch(error => console.error('Error resuming leave:', error));
  };

  return (
    <div>
      <Button variant="outline" onClick={() => navigate(-1)}>
        <IconArrowLeft size="1rem" />
        Back
      </Button>
      <Table withBorder withColumnBorders>
        <thead>
          <tr>
            <th>Date Range</th>
            <th>Days</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {leaves.map(leave => (
            <tr key={leave.id}>
              <td>{`${new Date(leave.start_date).toLocaleDateString()} - ${new Date(leave.end_date).toLocaleDateString()}`}</td>
              <td>{leave.days_count}</td>
              <td>
                <Badge color={leave.status === LeaveStatus.PENDING ? 'orange' : leave.status === LeaveStatus.APPROVED ? 'green' : 'red'}>{leave.status}</Badge>
              </td>
              <td>
                <Group spacing="xs">
                  {leave.status === LeaveStatus.PENDING && (
                    <Button color="orange" onClick={() => handleWithdraw(leave.id)}>
                      Withdraw
                    </Button>
                  )}
                  {leave.status === LeaveStatus.APPROVED && new Date(leave.start_date) > new Date() && (
                    <Button color="red" onClick={() => handleCancel(leave.id)}>
                      Cancel
                    </Button>
                  )}
                  {leave.status === LeaveStatus.CANCELLED && (
                    <Button color="green" onClick={() => handleResumption(leave.id)}>
                      Resume
                    </Button>
                  )}
                </Group>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
};

export default MyLeavesPage;