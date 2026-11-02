import React, { useState } from 'react';
import { Card, Title, Table, Button, Badge, Group, Modal, TextInput } from '@mantine/core';

interface Requisition {
  id: string;
  status: string;
  visitorName: string;
  roomNumber: number;
}

const CaretakerDashboardPage = () => {
  const [requisitions, setRequisitions] = useState<Requisition[]>([]); // Fetch requisitions from API
  const [selectedRequisitionId, setSelectedRequisitionId] = useState('');
  const [reasonModalOpened, setReasonModalOpened] = useState(false);
  
  const handleForwardClick = (id: string) => {
    // Implement forwarding logic here
  };

  const handleRejectClick = (id: string) => {
    setSelectedRequisitionId(id);
    setReasonModalOpened(true);
  };

  return (
    <Card>
      <Title order={2}>Pending Requisitions</Title>
      <Table>
        <thead>
          <tr>
            <th>Visitor Name</th>
            <th>Room Number</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {requisitions.map(req => (
            <tr key={req.id}>
              <td>{req.visitorName}</td>
              <td>{req.roomNumber}</td>
              <td><Badge color="blue">Pending</Badge></td>
              <td>
                <Group spacing="xs">
                  <Button onClick={() => handleForwardClick(req.id)}>Forward to In-Charge</Button>
                  <Button onClick={() => handleRejectClick(req.id)} color="red">Reject</Button>
                                <Modal opened={reasonModalOpened && selectedRequisitionId === req.id} onClose={() => setReasonModalOpened(false)} title="Enter Reason for Rejection">
                  <TextInput placeholder="Reason" />
                </Modal>
                </Group>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
};

export default CaretakerDashboardPage;
