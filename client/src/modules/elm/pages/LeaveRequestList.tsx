// Leave Request List
import { Table, Badge, Paper, Stack, Title, Button, LoadingOverlay, Text } from '@mantine/core';
import { useLeaveRequests, useApproveLeave } from '../api/hooks';
import { useNavigate } from 'react-router-dom';

export default function LeaveRequestList() {
  const { data, isLoading, error } = useLeaveRequests();
  const { mutateAsync } = useApproveLeave();
  const navigate = useNavigate();

  if (isLoading) return (
    <Paper p="md">
      <LoadingOverlay visible={true} overlayProps={{ opacity: 0.1 }}>
        <Title order={3}>Leave Requests</Title>
        <Text>Loading requests...</Text>
      </LoadingOverlay>
    </Paper>
  );

  if (error) return (
    <Paper p="md">
      <Title order={3}>Leave Requests</Title>
      <Text color="red">{error.message}</Text>
    </Paper>
  );

  return (
    <Paper p="md">
      <Title order={3}>Leave Requests</Title>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>Employee</Table.Th>
            <Table.Th>Start Date</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((request: Record<string, any>) => (
            <Table.Tr key={request.id}>
              <Table.Td>{request.id}</Table.Td>
              <Table.Td>{request.employee.name}</Table.Td>
              <Table.Td>{request.start_date}</Table.Td>
              <Table.Td>
                <Badge color={request.status === 'APPROVED' ? 'green' : 'yellow'}>
                  {request.status}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Stack>
                  <Button
                    variant="default"
                    onClick={() => navigate(`/elm/requests/${request.id}`)}
                  >
                    View
                  </Button>
                  {request.status === 'PENDING' && (
                    <Button
                      color="blue"
                      onClick={() => mutateAsync({ request_id: request.id, status: 'APPROVED' })}
                    >
                      Approve
                    </Button>
                  )}
                  {request.status === 'PENDING' && (
                    <Button
                      color="red"
                      onClick={() => mutateAsync({ request_id: request.id, status: 'REJECTED' })}
                    >
                      Reject
                    </Button>
                  )}
                </Stack>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  );
}
