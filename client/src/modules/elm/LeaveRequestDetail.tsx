import React from 'react';
import { useParams, useQuery } from 'react-router-dom';
import { LeaveRequest } from '../api/types';

const LeaveRequestDetail: React.FC = () => {
  const { id } = useParams();
  const { data, isLoading, isError } = useQuery<LeaveRequest>(`leave-request-${id}`, () => fetch(`/api/v1/leave-requests/${id}/`).then(res => res.json()));

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error</div>;

  return (
    <div>
      <h1>Leave Request Details</h1>
      <p>User: {data.user.username}</p>
      <p>Start Date: {data.start_date}</p>
      <p>End Date: {data.end_date}</p>
      <p>Reason: {data.reason}</p>
      <p>Status: {data.status}</p>
    </div>
  );
};

export default LeaveRequestDetail;
