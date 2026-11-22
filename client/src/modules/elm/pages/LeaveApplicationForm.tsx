import { useState } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  NumberInput,
  Select,
  Stack,
  Textarea,
  TextInput,
} from '@mantine/core';

import type { LeaveInput } from '../api/hooks';
import { useCreateLeave, useLeaveTypes } from '../api/hooks';

const LeaveApplicationForm = () => {
  const [form, setForm] = useState<LeaveInput>({
    leave_type: 0,
    start_date: '',
    end_date: '',
    purpose: '',
    half_day: 'FULL',
    substitute: null,
    station_leave: false,
    station_details: '',
    medical_evidence: '',
  });
  const [submitted, setSubmitted] = useState(false);

  const { data: leaveTypes, error: typesError } = useLeaveTypes();
  const { mutateAsync: createLeave, isPending, error } = useCreateLeave();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (name: 'leave_type' | 'half_day', value: string | null) => {
    setForm(prev => ({
      ...prev,
      [name]: name === 'leave_type' ? Number(value ?? 0) : value ?? 'FULL'
    }));
  };
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(false);

    try {
      createLeave(form)
        .then(() => setSubmitted(true))
        .catch(() => setSubmitted(false));
    } catch (err) {
      setSubmitted(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        {typesError && (
          <Alert color="red" title="Error loading leave types">
            {typesError.message}
          </Alert>
        )}

        <Select
          label="Leave Category"
          data={leaveTypes?.filter(type =>
            ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL'].includes(type.type)
          ).map(type => ({
            label: type.type,
            value: String(type.id),
          })) || []}
          value={String(form.leave_type)}
          onChange={(value) => handleSelectChange('leave_type', value)}
          required
          disabled={isPending}
        />

        <Stack>
          <TextInput
            label="Start Date"
            type="date"
            value={form.start_date}
            onChange={handleInputChange}
            name="start_date"
            required
          />
          <TextInput
            label="End Date"
            type="date"
            value={form.end_date}
            onChange={handleInputChange}
            name="end_date"
            required
          />
        </Stack>

        <Textarea
          label="Purpose"
          value={form.purpose}
          onChange={handleInputChange}
          name="purpose"
          required
          minRows={3}
        />

        {leaveTypes.find(i => i.id === form.leave_type)?.type === 'CL' && (
          <Select
            label="Half Day"
            data={['FULL', 'FIRST', 'SECOND']}
            value={form.half_day}
            onChange={(value) => handleSelectChange('half_day', value)}
          />
        )}

        <NumberInput
          label="Substitute employee ID"
          value={form.substitute ?? ''}
          onChange={(value) => setForm(prev => ({ ...prev, substitute: value === '' ? null : Number(value) }))}
          name="substitute"
          placeholder="Leave empty if none"
        />

        <Checkbox
          label="Station Leave"
          checked={form.station_leave}
          onChange={(e) => setForm(prev => ({ ...prev, station_leave: e.target.checked }))}
          name="station_leave"
        />

        {form.station_leave && (
          <Textarea
            label="Station Details"
            value={form.station_details}
            onChange={handleInputChange}
            name="station_details"
            required
            minRows={3}
          />
        )}

        <TextInput
          label="Medical Evidence Reference"
          value={form.medical_evidence}
          onChange={handleInputChange}
          name="medical_evidence"
          placeholder="Optional"
        />

        {error && (
          <Alert color="red" title="Error submitting request">
            {error.message}
          </Alert>
        )}

        {submitted && (
          <Alert color="green" title="Request Submitted">
            Request submitted for review. Balance changes only after final approval.
          </Alert>
        )}

        <Button
          type="submit"
          loading={isPending}
          disabled={!form.leave_type || isPending}
        >
          Submit Leave Request
        </Button>
      </Stack>
    </form>
  );
};

export default LeaveApplicationForm;
