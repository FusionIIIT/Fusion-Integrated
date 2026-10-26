import { useLeaveBalances } from '../api/hooks';
import { useLeaveTypes } from '../api/hooks';
import { Paper, Title, Text, Table, Alert } from '@mantine/core';

const LeaveBalanceDashboard = () => {
  const { data: balancesData, isLoading: balancesLoading, error: balancesError } = useLeaveBalances();
  const { data: typesData, isLoading: typesLoading, error: typesError } = useLeaveTypes();

  if (balancesError) {
    return (
      <Paper>
        <Title order={2}>Leave Balances</Title>
        <Alert color="red" title="Error loading leave balances">
          {balancesError.message}
        </Alert>
      </Paper>
    );
  }

  if (typesError) {
    return (
      <Paper>
        <Title order={2}>Leave Balances</Title>
        <Alert color="red" title="Error loading leave types">
          {typesError.message}
        </Alert>
      </Paper>
    );
  }

  if (balancesLoading || typesLoading) {
    return (
      <Paper>
        <Title order={2}>Leave Balances</Title>
        <Text>Loading data...</Text>
      </Paper>
    );
  }

  if (!balancesData || !typesData || balancesData.length === 0) {
    return (
      <Paper>
        <Title order={2}>Leave Balances</Title>
        <Text>No data found.</Text>
      </Paper>
    );
  }

  const mappedBalances = balancesData.map((balance) => {
    const type = typesData.find((type) => type.id === balance.leave_type);
    return {
      ...balance,
      category: type ? type.type : 'Unknown',
    };
  });

  return (
    <Paper>
      <Title order={2}>Leave Balances</Title>
      <Table>
        <thead>
          <tr>
            <th>Employee</th>
            <th>Category</th>
            <th>Year</th>
            <th>Available days</th>
          </tr>
        </thead>
        <tbody>
          {mappedBalances.map((balance) => (
            <tr key={balance.id}>
              <td>{balance.employee}</td>
              <td>{balance.category}</td>
              <td>{balance.year}</td>
              <td>{balance.balance}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Paper>
  );
};

export default LeaveBalanceDashboard;
