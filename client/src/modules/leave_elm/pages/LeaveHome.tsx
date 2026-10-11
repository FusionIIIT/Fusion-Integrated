import { useState, useEffect, type FormEvent } from 'react';
import { Container, Stack, Title, TextInput, Textarea, Select, Checkbox, Button, Alert } from '@mantine/core';
import { http } from '../../../lib/http';

const LeaveHome = () => {
  const [category, setCategory] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [purpose, setPurpose] = useState('');
  const [stationLeave, setStationLeave] = useState(false);
  const [halfDay, setHalfDay] = useState(false);
  const [substituteEmployeeId, setSubstituteEmployeeId] = useState('');
  const [requestedDays, setRequestedDays] = useState('');

  useEffect(() => {
    loadLeaveRequests();
    loadLeaveBalances();
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      const response = await http.post('/leave_elm/requests', {
        category,
        start_date: startDate,
        end_date: endDate,
        purpose,
        station_leave: stationLeave,
        half_day: halfDay,
        substitute_employee_id: substituteEmployeeId,
        requested_days: requestedDays,
      });

      console.log(response);
    } catch (error) {
      console.error(error);
    }
  };

  const loadLeaveRequests = async () => {
    try {
      const response = await http.get('/leave_elm/requests');
      console.log(response);
    } catch (error) {
      console.error(error);
    }
  };

  const loadLeaveBalances = async () => {
    try {
      const response = await http.get('/leave_elm/balances');
      console.log(response);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <Container>
      <Stack>
        <Title order={1}>Leave Request Form</Title>

        <form onSubmit={handleSubmit}>
          <Select
            label="Category"
            data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
            value={category}
            onChange={(value) => setCategory(value ?? "")}
            required
          />

          <TextInput label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.currentTarget.value)} required />
          <TextInput label="End date" type="date" value={endDate} onChange={(e) => setEndDate(e.currentTarget.value)} required />

          <Textarea
            label="Purpose"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />

          <Checkbox label="Station Leave" checked={stationLeave} onChange={(e) => setStationLeave(e.currentTarget.checked)} />

          <Checkbox
            label="Half Day"
            checked={halfDay}
            onChange={(e) => setHalfDay(e.target.checked)}
          />

          <TextInput
            label="Substitute Employee ID"
            value={substituteEmployeeId}
            onChange={(e) => setSubstituteEmployeeId(e.target.value)}
          />

          <TextInput
            label="Requested Days"
            value={requestedDays}
            onChange={(e) => setRequestedDays(e.target.value)}
          />

          <Button type="submit">Submit</Button>
        </form>
      </Stack>
    </Container>
  );
};

export default LeaveHome;
