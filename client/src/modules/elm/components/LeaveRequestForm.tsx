import React, { useState } from 'react';
import { useMutation } from 'react-query';
import { leaveManagementApi } from '../api';

const LeaveRequestForm: React.FC = () => {
  const [formData, setFormData] = useState({
    leave_type: '',
    start_date: '',
    end_date: '',
  });

  const { mutate, isLoading, isError, error } = useMutation(
    'createLeaveRequest',
    leaveManagementApi.createLeaveRequest,
    {
      onSuccess: () => {
        // Handle success
      },
      onError: (err) => {
        // Handle error
      },
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate(formData);
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Leave Type:
        <input
          type="text"
          value={formData.leave_type}
          onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
        />
      </label>
      <label>
        Start Date:
        <input
          type="date"
          value={formData.start_date}
          onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
        />
      </label>
      <label>
        End Date:
        <input
          type="date"
          value={formData.end_date}
          onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
        />
      </label>
      <button type="submit" disabled={isLoading}>
        Submit
      </button>
      {isError && <div>Error: {error.message}</div>}
    </form>
  );
};

export default LeaveRequestForm;