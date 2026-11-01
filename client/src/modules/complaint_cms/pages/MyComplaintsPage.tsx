import { useState } from 'react';
import { Group, Stack, Text, Title, TextInput, Textarea, Select, Button, Table, Pagination, ActionIcon, Tooltip, Modal, NumberInput } from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { submitComplaint, complaintAction, getConfiguration, type Complaint } from '../api';
import { PageHeader } from '../../../ui/components/PageHeader';

const MyComplaintsPage = () => {
  const [complaintForm, setComplaintForm] = useState<Record<string, any>>({
    category: '',
    title: '',
    description: '',
    location_type: '',
    location_details: '',
    severity: ''
  });
  const [openModal, setOpenModal] = useState(false);
  const queryClient = useQueryClient();

  const handleLodgeComplaint = async () => {
    try {
      await submitComplaint(complaintForm as any);
      queryClient.invalidateQueries({ queryKey: ['list-complaints'] });
      setComplaintForm({
        category: '',
        title: '',
        description: '',
        location_type: '',
        location_details: '',
        severity: ''
      });
    } catch (error) {
      console.error('Error lodging complaint:', error);
    }
  };

  const columns: Array<{ accessorKey: string; header?: string; cell?: (args: { row: any }) => any }> = [
    { accessorKey: 'tracking_code', header: 'Tracking Code' },
    { accessorKey: 'title', header: 'Title' },
    { accessorKey: 'severity', header: 'Severity' },
    { accessorKey: 'status', header: 'Status' },
    {
      accessorKey: 'action',
      cell: ({ row }: { row: any }) => (
        <Group gap="sm">
          <Tooltip label="Reopen Complaint" position="top">
            <ActionIcon onClick={() => complaintAction(row.original.id, 'reopen')}>
              <Text size="xs">↗</Text>
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Feedback" position="top">
            <ActionIcon onClick={() => complaintAction(row.original.id, 'feedback')}>
              <Text size="xs">★</Text>
            </ActionIcon>
          </Tooltip>
        </Group>
      )
    }
  ];

  return (
    <>
      <PageHeader title="My Complaints" subtitle={(getConfiguration() as any).company_name} action={
        <Button variant="outline" color="blue" onClick={() => setOpenModal(true)}>
          Lodge New Complaint
        </Button>
      } />

      <Modal opened={openModal} onClose={() => setOpenModal(false)} centered size="lg">
        <Stack gap={4}>
          <Title order={3}>Lodge a new complaint</Title>

          <TextInput
            placeholder="Category"
            value={complaintForm.category}
            onChange={(e) => setComplaintForm({ ...complaintForm, category: e.target.value })}
          />

          <TextInput
            placeholder="Title"
            value={complaintForm.title}
            onChange={(e) => setComplaintForm({ ...complaintForm, title: e.target.value })}
          />

          <Textarea
            placeholder="Description"
            value={complaintForm.description}
            onChange={(e) => setComplaintForm({ ...complaintForm, description: e.target.value })}
          />

          <Select
            label="Location Type"
            value={complaintForm.location_type}
            onChange={(value) => setComplaintForm({ ...complaintForm, location_type: value ?? '' })}
            data={[
              { value: 'building', label: 'Building' },
              { value: 'facility', label: 'Facility' }
            ]}
          />

          <Group>
            <NumberInput
              label="Severity (1-5)"
              min={1}
              max={5}
              value={complaintForm.severity as number}
              onChange={(value) => setComplaintForm({ ...complaintForm, severity: value })}
            />
            <Tooltip label="Scale from 1 to 5" position="top">
              <Text size="sm" c="dimmed" style={{ marginLeft: 4 }}>i</Text>
            </Tooltip>
          </Group>

          <Button variant="outline" color="blue" onClick={() => setOpenModal(false)}>
            Cancel
          </Button>
          <Button variant="filled" color="green" onClick={handleLodgeComplaint}>
            Lodge Complaint
          </Button>
        </Stack>
      </Modal>

      <Table style={{ minWidth: 700 }}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.accessorKey}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(queryClient.getQueryData<Complaint[]>(['list-complaints']) ?? []).map((row: any) => (
            <tr key={row.tracking_code}>
              {columns.map((column) => (
                <td key={column.accessorKey}>
                  {typeof column.cell === 'function' ? column.cell({ row }) : row[column.accessorKey]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>

      <Pagination
        total={10}
        value={1}
        onChange={(page) => console.log(page)}
      />
    </>
  );
};

export default MyComplaintsPage;
