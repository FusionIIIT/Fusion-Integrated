import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { LeaveRequest } from '../api/types';

const LeaveRequestList: React.FC = () => {
  const { data, isLoading, isError } = useQuery<LeaveRequest[]>('leave-requests', () => fetch('/api/v1/leave-requests/').then(res => res.json()));

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error</div>;

  return (
    <div>
      <h1>Leave Requests</h1>
      <ul>
        {data.map(request => (
          <li key={request.id}>
            <Link to={`/leave-requests/${request.id}`}>{request.user.username} - {request.start_date} to {request.end_date}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default LeaveRequestList;
