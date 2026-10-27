import React, { useState } from 'react';
import { Button, Checkbox, DatePicker, Group, Input, Select, Textarea } from '@mantine/core';
import { useForm } from '@mantine/hooks';
import { Category, Employee, LeaveRequest } from '../api/types';

interface ApplyLeavePageProps {
  categories: Category[];
  employees: Employee[];
}

const ApplyLeavePage: React.FC<ApplyLeavePageProps> = ({ categories, employees }) => {
  const form = useForm<LeaveRequest>({
    initialValues: {
      category: '',
      startDate: null,
      endDate: null,
      isHalfDay: false,
      stationLeave: false,
      stationName: '',
      substituteId: null,
      purpose: '',
    },
  });

  const [substituteOptions, setSubstituteOptions] = useState<Employee[]>([]);

  useEffect(() => {
    if (form.values.substituteId) {
      const selectedEmployee = employees.find(emp => emp.id === form.values.substituteId);
      if (selectedEmployee) {
        setSubstituteOptions([selectedEmployee]);
      } else {
        setSubstituteOptions(employees);
      }
    } else {
      setSubstituteOptions(employees);
    }
  }, [form.values.substituteId, employees]);

  const handleSubmit = async (values: LeaveRequest) => {
    // Handle form submission logic here
    console.log('Leave Request Submitted:', values);
  };

  return (
    <div>
      <h1>Apply for Leave</h1>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Group direction="column" spacing="md">
          <Select
            label="Category"
            data={categories.map(cat => ({ value: cat.code, label: cat.name }))}
            {...form.getInputProps('category')}
          />
          <DatePicker
            label="Start Date"
            {...form.getInputProps('startDate', { type: 'date' })}
          />
          <DatePicker
            label="End Date"
            {...form.getInputProps('endDate', { type: 'date' })}
          />
          <Checkbox
            label="Half Day (First Half)"
            checked={form.values.isHalfDay}
            onChange={(e) => form.setFieldValue('isHalfDay', e.currentTarget.checked)}
            disabled={form.values.category !== 'CL'}
          />
          <Checkbox
            label="Station Leave"
            checked={form.values.stationLeave}
            onChange={(e) => form.setFieldValue('stationLeave', e.currentTarget.checked)}
          />
          {form.values.stationLeave && (
            <>
              <Input.Wrapper label="Station Name">
                <Input {...form.getInputProps('stationName')} />
              </Input.Wrapper>
            </>
          )}
          <Select
            label="Substitute"
            data={substituteOptions.map(emp => ({ value: emp.id, label: `${emp.firstName} ${emp.lastName}` }))}
            {...form.getInputProps('substituteId')}
          />
          <Textarea
            label="Purpose"
            {...form.getInputProps('purpose')}
          />
          <Button type="submit">Submit</Button>
        </Group>
      </form>
    </div>
  );
};

export default ApplyLeavePage;