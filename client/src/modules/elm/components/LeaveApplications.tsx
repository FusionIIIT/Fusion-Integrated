import React, { useEffect, useState } from 'react';
import { Form, Button, Table } from '@fusion/components';
import { getLeaveApplications, createLeaveApplication } from '../../api';

const LeaveApplications: React.FC = () => {
  const [applications, setApplications] = useState([]);
  const [formData, setFormData] = useState({});

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    const res = await getLeaveApplications();
    setApplications(res.data);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createLeaveApplication(formData);
    fetchApplications();
  };

  return (
    <div>
      <h1>Leave Applications</h1>
      <Table data={applications} columns={['employee', 'leave_type', 'start_date', 'end_date', 'status']} />
      <h2>Submit a Leave Application</h2>
      <Form onSubmit={handleSubmit}>
        <Form.Input name="employee" label="Employee" onChange={setFormData} />
        <Form.Input name="leave_type" label="Leave Type" onChange={setFormData} />
        <Form.Input name="start_date" label="Start Date" type="date" onChange={setFormData} />
        <Form.Input name="end_date" label="End Date" type="date" onChange={setFormData} />
        <Button type="submit">Submit</Button>
      </Form>
    </div>
  );
};

export default LeaveApplications;
