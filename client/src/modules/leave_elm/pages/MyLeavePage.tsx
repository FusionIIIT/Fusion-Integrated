import { useEffect } from 'react';
import { Button, Grid, TextInput, Select, Textarea, Title } from '@mantine/core';
import { useForm } from 'react-hook-form';
import { useQueryClient } from '@tanstack/react-query';

import { listApplications, submitApplication, type LeaveApplication, type NewApplication } from '../api';
type ListApplicationsResponse = LeaveApplication[];
type SubmitApplicationRequest = Omit<NewApplication, 'leave_type'> & { leave_type: string };

const MyLeavePage = () => {
  const queryClient = useQueryClient();
  const { handleSubmit, register, setValue } = useForm<SubmitApplicationRequest>({
    defaultValues: {
      leave_type: '',
      start_date: '',
      end_date: '',
      purpose: ''
    }
  });

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const applications = await listApplications();
        console.log('Applications:', applications);
      } catch (error) {
        console.error('Error fetching applications:', error);
      }
    };

    fetchApplications();
  }, []);

  return (
    <Grid>
      <Grid.Col span={12}>
        <Title order={3}>Your Leave Applications</Title>
        <Textarea value={JSON.stringify(queryClient.getQueryData<ListApplicationsResponse>(['applications']), null, 2)} />
      </Grid.Col>

      <Grid.Col span={6}>
        <Title order={4}>New Application Form</Title>
        <form onSubmit={handleSubmit((data) => submitApplication(data as unknown as NewApplication))}>
          <TextInput
            label="Start Date"
            type="date"
            {...register('start_date')}
          />

          <TextInput
            label="End Date"
            type="date"
            {...register('end_date')}
          />

          <Select
            label="Leave Type"
            placeholder="Choose a leave type"
            data={[
              { value: 'vacation', label: 'Vacation' },
              { value: 'sick_leave', label: 'Sick Leave' },
              // Add more options as needed
            ]}
            onChange={(value) => setValue("leave_type", value ?? "")}
          />

          <Textarea
            label="Purpose"
            {...register('purpose')}
          />

          <Button type="submit">Submit Application</Button>
        </form>
      </Grid.Col>

      {/* Render application actions here */}
    </Grid>
  );
};

export default MyLeavePage;
