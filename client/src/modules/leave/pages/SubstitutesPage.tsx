import React, { useState, useEffect } from 'react';
import { Button, Table, Text, Group, Modal } from '@mantine/core';
import { IconCheck, IconX } from '@tabler/icons-react';
import { useAuth } from '../../auth/useAuth';
import { getSubstituteRequests, acceptSubstituteRequest, declineSubstituteRequest } from '../api';

interface SubstituteRequest {
  id: number;
  applicant: string;
  startDate: Date;
  endDate: Date;
  responsibilities: string;
  status: 'pending' | 'accepted' | 'declined';
}

const SubstitutesPage: React.FC = () => {
  const { user } = useAuth();
  const [substituteRequests, setSubstituteRequests] = useState<SubstituteRequest[]>([]);
  const [acceptModalOpen, setAcceptModalOpen] = useState(false);
  const [declineModalOpen, setDeclineModalOpen] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);

  useEffect(() => {
    if (user) {
      getSubstituteRequests(user.id).then((requests) => {
        setSubstituteRequests(requests);
      });
    }
  }, [user]);

  const handleAcceptRequest = () => {
    if (selectedRequestId !== null) {
      acceptSubstituteRequest(selectedRequestId).then(() => {
        setSubstituteRequests((prevRequests) =>
          prevRequests.map((req) =>
            req.id === selectedRequestId ? { ...req, status: 'accepted' } : req
          )
        );
        setAcceptModalOpen(false);
      });
    }
  };

  const handleDeclineRequest = () => {
    if (selectedRequestId !== null) {
      declineSubstituteRequest(selectedRequestId).then(() => {
        setSubstituteRequests((prevRequests) =>
          prevRequests.map((req) =>
            req.id === selectedRequestId ? { ...req, status: 'declined' } : req
          )
        );
        setDeclineModalOpen(false);
      });
    }
  };

  return (
    <div>
      <Table withBorder striped highlightOnHover>
        <thead>
          <tr>
            <th>Applicant</th>
            <th>Dates</th>
            <th>Responsibilities</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {substituteRequests.map((request) => (
            <tr key={request.id}>
              <td>{request.applicant}</td>
              <td>{`${request.startDate.toDateString()} - ${request.endDate.toDateString()}`}</td>
              <td>{request.responsibilities}</td>
              <td>{request.status}</td>
              <td>
                {request.status === 'pending' && (
                  <>
                    <Button
                      color="green"
                      onClick={() => {
                        setSelectedRequestId(request.id);
                        setAcceptModalOpen(true);
                      }}
                    >
                      Accept
                    </Button>
                    <Button
                      color="red"
                      onClick={() => {
                        setSelectedRequestId(request.id);
                        setDeclineModalOpen(true);
                      }}
                    >
                      Decline
                    </Button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Modal
        opened={acceptModalOpen}
        onClose={() => setAcceptModalOpen(false)}
        title="Confirm Acceptance"
      >
        <Text>Are you sure you want to accept this substitute request?</Text>
        <Group position="right" mt="md">
          <Button onClick={() => setAcceptModalOpen(false)}>Cancel</Button>
          <Button color="green" onClick={handleAcceptRequest}>
            Accept
          </Button>
        </Group>
      </Modal>

      <Modal
        opened={declineModalOpen}
        onClose={() => setDeclineModalOpen(false)}
        title="Confirm Decline"
      >
        <Text>Are you sure you want to decline this substitute request?</Text>
        <Group position="right" mt="md">
          <Button onClick={() => setDeclineModalOpen(false)}>Cancel</Button>
          <Button color="red" onClick={handleDeclineRequest}>
            Decline
          </Button>
        </Group>
      </Modal>
    </div>
  );
};

export default SubstitutesPage;