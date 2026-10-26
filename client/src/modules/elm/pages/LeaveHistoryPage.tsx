import React from 'react';

interface LeaveHistoryPageProps {
  leaves: {
    leaveType: string;
    startDate: string;
    endDate: string;
    status: string;
  }[];
}

const LeaveHistoryPage: React.FC<LeaveHistoryPageProps> = ({ leaves }) => {
  return (
    <div>
      <h1>Leave History</h1>
      <table>
        <thead>
          <tr>
            <th>Leave Type</th>
            <th>Start Date</th>
            <th>End Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {leaves.map((leave, index) => (
            <tr key={index}>
              <td>{leave.leaveType}</td>
              <td>{leave.startDate}</td>
              <td>{leave.endDate}</td>
              <td>{leave.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeaveHistoryPage;