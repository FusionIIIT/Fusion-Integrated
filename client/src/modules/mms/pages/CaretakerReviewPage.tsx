import React, { useState } from 'react';
import { Paper, Title, SegmentedControl, Table, Button, Group, Stack, Text } from '@mantine/core';
import { useMmsReports, useReviewRequest } from '../api/queries';

export default function CaretakerReviewPage() {
  const [section, setSection] = useState('registrations');
  const { data: records, isLoading } = useMmsReports(section);
  const reviewMutation = useReviewRequest();

  const handleAction = (id: number, decision: string) => {
    const typeMapping: Record<string, string> = {
      registrations: 'registration',
      rebates: 'rebate',
      'special-meals': 'special-food',
    };
    reviewMutation.mutate({ moduleType: typeMapping[section] || 'registration', id, decision });
  };

  return (
    <Stack gap="lg" p="md">
      <Title order={2}>MMS Caretaker Operational Review</Title>
      <SegmentedControl
        value={section}
        onChange={setSection}
        data={[
          { label: 'Registrations', value: 'registrations' },
          { label: 'Rebates', value: 'rebates' },
          { label: 'Special Meals', value: 'special-meals' },
          { label: 'Vacation Survey', value: 'vacation-summary' },
        ]}
      />

      <Paper p="md" withBorder radius="md">
        <Table striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Status / Details</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {!isLoading && records && records.length > 0 ? (
              records.map((r: any) => (
                <Table.Tr key={r.id}>
                  <Table.Td>#{r.id}</Table.Td>
                  <Table.Td>
                    Status: {r.status || r.response} | Details: {r.reason || r.vacation_name || 'N/A'}
                  </Table.Td>
                  <Table.Td>
                    {r.status === 'pending' || r.status === 'requested' ? (
                      <Group gap="xs">
                        <Button size="xs" color="green" onClick={() => handleAction(r.id, 'approve')}>
                          Approve
                        </Button>
                        <Button size="xs" color="red" onClick={() => handleAction(r.id, 'reject')}>
                          Reject
                        </Button>
                      </Group>
                    ) : (
                      <Text size="sm" c="dimmed">Completed</Text>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))
            ) : (
              <Table.Tr>
                <Table.Td colSpan={3}><Text ta="center">No active records for this tab.</Text></Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}