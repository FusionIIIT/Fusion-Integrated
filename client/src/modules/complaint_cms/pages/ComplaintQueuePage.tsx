import { useEffect } from 'react';
import { Group, Stack, Text, Title, Button, Input, Select, Textarea, Tooltip } from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { errorMessage as ErrorMessage } from '../../../lib/http';
import { PageHeader } from '../../../ui/components/PageHeader';
import { complaintAction, listComplaints, listTasks } from '../api';

interface Task {
  id?: number;
  title?: string;
  status: string;
}

interface Complaint {
  id?: number;
  title?: string;
  description?: string;
  status: string;
}

const ComplaintQueuePage = () => {
  const queryClient = useQueryClient();

  // Fetch assigned tasks for the current user
  const { data: tasksData, error: taskError, isLoading: isTasksLoading } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async () => listTasks(0), // Assuming 0 represents the current user's ID
  });

  // Fetch complaints
  const { error: complaintError } = useQuery<Complaint[]>({
    queryKey: ['complaints'],
    queryFn: async () => listComplaints(),
  });

  // Handle action button clicks
  const handleActionClick = (id: number, action: string, data?: Record<string, unknown>) => {
    complaintAction(id, action, data).then(() => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['complaints'] });
    });
  };

  useEffect(() => {
    if (taskError || complaintError) {
      console.error('Error fetching data:', ErrorMessage(taskError));
    }
  }, [taskError, complaintError]);

  return (
    <Stack>
      <PageHeader title="Complaint Queue" />
      {isTasksLoading && <Text>Loading tasks...</Text>}
      {!isTasksLoading && tasksData?.length === 0 && <Text>No assigned tasks found.</Text>}
      {tasksData?.map((task) => (
        <Group key={task.id} mb="sm">
          <Title order={3}>{task.title}</Title>
          <Select
            label="Status"
            value={task.status}
            onChange={(status) => handleActionClick(task.id ?? 0, 'update_status', { status })}
            data={[
              { value: 'pending', label: 'Pending' },
              { value: 'in_progress', label: 'In Progress' },
              { value: 'resolved', label: 'Resolved' },
              { value: 'escalated', label: 'Escalated' },
              { value: 'closed', label: 'Closed' },
            ]}
          />
          <Input.Wrapper required error={taskError ? ErrorMessage(taskError) : undefined}>
            <Tooltip label="Comment/Resolution">
              <Textarea
                placeholder="Enter comment or resolution"
                value=""
                onChange={() => {}}
              />
            </Tooltip>
          </Input.Wrapper>
          <Group gap="xs">
            <Button onClick={() => handleActionClick(task.id ?? 0, 'acknowledge')}>Acknowledge</Button>
            <Button onClick={() => handleActionClick(task.id ?? 0, 'start_progress')}>Start Progress</Button>
            <Button onClick={() => handleActionClick(task.id ?? 0, 'resolve')}>Resolve</Button>
            <Button onClick={() => handleActionClick(task.id ?? 0, ' escalate')}>Escalate</Button>
            <Button onClick={() => handleActionClick(task.id ?? 0, 'close')}>Close</Button>
          </Group>
        </Group>
      ))}
    </Stack>
  );
};

export default ComplaintQueuePage;
