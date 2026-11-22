// Leave Policy Editor
import { Table, Badge, Paper, Stack, Title, Button, LoadingOverlay, Text } from '@mantine/core';
import { useLeavePolicies } from '../api/hooks';
import { useNavigate } from 'react-router-dom';

export default function LeavePolicyEditor() {
  const { data, isLoading, error } = useLeavePolicies();
  const navigate = useNavigate();

  if (isLoading) return (
    <Paper p="md">
      <LoadingOverlay visible={true} overlayProps={{ opacity: 0.1 }}>
        <Title order={3}>Leave Policies</Title>
        <Text>Loading policies...</Text>
      </LoadingOverlay>
    </Paper>
  );

  if (error) return (
    <Paper p="md">
      <Title order={3}>Leave Policies</Title>
      <Text color="red">{error.message}</Text>
    </Paper>
  );

  return (
    <Paper p="md">
      <Title order={3}>Leave Policies</Title>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Description</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((policy: Record<string, any>) => (
            <Table.Tr key={policy.id}>
              <Table.Td>{policy.name}</Table.Td>
              <Table.Td>{policy.description}</Table.Td>
              <Table.Td>
                <Badge color={policy.status === 'ACTIVE' ? 'green' : 'yellow'}>
                  {policy.status}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Stack>
                  <Button
                    variant="default"
                    onClick={() => navigate(`/elm/policies/${policy.id}`)}
                  >
                    View
                  </Button>
                  <Button
                    color="blue"
                    onClick={() => navigate(`/elm/policies/${policy.id}/edit`)}
                  >
                    Edit
                  </Button>
                </Stack>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  );
}
