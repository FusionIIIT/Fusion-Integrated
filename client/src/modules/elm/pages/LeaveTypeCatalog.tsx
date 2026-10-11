// Leave Type Catalog
import { Table, Badge, Paper, Stack, Title, Button, LoadingOverlay, Text } from '@mantine/core';
import { useLeaveTypes } from '../api/hooks';
import { useNavigate } from 'react-router-dom';

export default function LeaveTypeCatalog() {
  const { data, isLoading, error } = useLeaveTypes();
  const navigate = useNavigate();

  if (isLoading) return (
    <Paper p="md">
      <LoadingOverlay visible={true} overlayProps={{ opacity: 0.1 }}>
        <Title order={3}>Leave Types</Title>
        <Text>Loading types...</Text>
      </LoadingOverlay>
    </Paper>
  );

  if (error) return (
    <Paper p="md">
      <Title order={3}>Leave Types</Title>
      <Text color="red">{error.message}</Text>
    </Paper>
  );

  return (
    <Paper p="md">
      <Title order={3}>Leave Types</Title>
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
          {data.map((type: Record<string, any>) => (
            <Table.Tr key={type.id}>
              <Table.Td>{type.name}</Table.Td>
              <Table.Td>{type.description}</Table.Td>
              <Table.Td>
                <Badge color={type.status === 'ACTIVE' ? 'green' : 'yellow'}>
                  {type.status}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Stack>
                  <Button
                    variant="default"
                    onClick={() => navigate(`/elm/types/${type.id}`)}
                  >
                    View
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
