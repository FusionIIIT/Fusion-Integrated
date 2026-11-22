import { useLeavePolicies } from '../api/hooks';
import { useLeaveTypes } from '../api/hooks';
import { Paper, Title, Text, Table, Alert } from '@mantine/core';

const LeavePolicyEditor = () => {
  const { data: leavePolicies, isLoading, error } = useLeavePolicies();
  const { data: leaveTypes } = useLeaveTypes();

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
    return <Paper> Loading leave policies...</Paper>;
  }

  if (!leavePolicies || leavePolicies.length === 0) {
    return (
      <Paper>
        <Title order={3}>Leave policies</Title>
        <Text>No leave policies found.</Text>
      </Paper>
    );
  }

  return (
    <Paper>
      <Title order={3}>Leave policies</Title>
      <Table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Applies to</th>
            <th>Maximum days</th>
            <th>Substitute required</th>
            <th>Medical evidence</th>
            <th>Reminder hours</th>
            <th>Escalation hours</th>
          </tr>
        </thead>
        <tbody>
          {leavePolicies.map((policy) => {
            const leaveType = leaveTypes?.find(
              (type) => type.id === policy.type
            );
            return (
              <tr key={policy.id}>
                <td>{leaveType?.type || 'Unknown'}</td>
                <td>{policy.applicable_kind || 'All employees'}</td>
                <td>{policy.max_days || 'No configured limit'}</td>
                <td>{policy.requires_substitute ? 'Yes' : 'No'}</td>
                <td>
                  {policy.medical_evidence_required ? 'Yes' : 'No'}
                </td>
                <td>{policy.reminder_hours}</td>
                <td>{policy.escalation_hours}</td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </Paper>
  );
};

export default LeavePolicyEditor;
