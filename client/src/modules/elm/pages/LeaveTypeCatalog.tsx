import { useLeaveTypes } from '../api/hooks';
import { Paper, Title, Text, Table, Alert } from '@mantine/core';

const typeMapping: Record<string, string> = {
  CL: 'Casual leave',
  RH: 'Restricted holiday',
  SCL: 'Special casual leave',
  EL: 'Earned leave',
  COL: 'Commuted leave',
  VL: 'Vacation leave',
};

const LeaveTypeCatalog = () => {
  const { data, isLoading, error } = useLeaveTypes();

  if (error) {
    return (
      <Paper>
        <Alert title="Error" color="red">
          {error.message}
        </Alert>
      </Paper>
    );
  }

  if (isLoading) {
    return (
      <Paper>
        <Text>Loading leave types...</Text>
      </Paper>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Paper>
        <Text>No leave types found.</Text>
      </Paper>
    );
  }

  return (
    <Paper>
      <Title order={2}>Leave categories</Title>
      <Table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Substitute required</th>
          </tr>
        </thead>
        <tbody>
          {data
            .filter((type) => ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL'].includes(type.type))
            .map((type) => (
              <tr key={type.id}>
                <td>{typeMapping[type.type]}</td>
                <td>{type.requires_substitute ? 'Yes' : 'No'}</td>
              </tr>
            ))}
        </tbody>
      </Table>
    </Paper>
  );
};

export default LeaveTypeCatalog;
