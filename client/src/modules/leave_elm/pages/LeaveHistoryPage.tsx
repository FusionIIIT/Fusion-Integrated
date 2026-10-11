import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../../../api'; // Assuming API client is available

interface LeaveHistoryPageProps {
  // No props needed for this simple component
}

const LeaveHistoryPage: React.FC<LeaveHistoryPageProps> = () => {
  const [leaveApplications, setLeaveApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const location = useLocation();

  useEffect(() => {
    const fetchLeaveApplications = async () => {
      try {
        const response = await api.get('/leave/history');
        setLeaveApplications(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching leave history:', error);
        setLoading(false);
      }
    };

    fetchLeaveApplications();
  }, []);

  const handleWithdraw = async (applicationId: string) => {
    try {
      await api.post(`/leave/application/${applicationId}/withdraw`);
      // Refresh the leaveApplications list after withdrawal
      const updatedApplications = leaveApplications.map(app =>
        app.id === applicationId ? { ...app, status: 'Withdrawn' } : app
      );
      setLeaveApplications(updatedApplications);
    } catch (error) {
      console.error('Error withdrawing leave application:', error);
    }
  };

  if (loading) {
    return <div>Loading leave history...</div>;
  }

  return (
    <div className="leave-history-page">
      <h2>Leave History</h2>
      <table>
        <thead>
          <tr>
            <th>Employee</th>
            <th>Date</th>
            <th>Leave Type</th>
            <th>Reason</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {leaveApplications.map((application) => (
            <tr key={application.id}>
              <td>{application.employeeName}</td>
              <td>{application.startDate} - {application.endDate}</td>
              <td>{application.leaveCategory}</td>
              <td>{application.reason}</td>
              <Badge status={application.status} />
              <td>
                {application.status === 'Pending' ? (
                  <button onClick={() => handleWithdraw(application.id)}>Withdraw</button>
                ) : (
                  <>
                    {application.status === 'Approved' ? (
                      <button disabled>Approved</button>
                    ) : (
                      application.status === 'Rejected' ? (
                        <button disabled>Rejected</button>
                      ) : null
                    )}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Helper component for displaying status badges
interface BadgeProps {
  status: 'Pending' | 'Approved' | 'Rejected' | 'Withdrawn';
}

const Badge: React.FC<BadgeProps> = ({ status }) => {
  switch (status) {
    case 'Pending':
      return <span className="pending-badge">Pending</span>;
    case 'Approved':
      return <span className="approved-badge">Approved</span>;
    case 'Rejected':
      return <span className="rejected-badge">Rejected</span>;
    case 'Withdrawn':
      return <span className="withdrawn-badge">Withdrawn</span>;
    default:
      return <span>Unknown</span>;
  }
};

export default LeaveHistoryPage;

interface LeaveApplication {
  id: string;
  employeeId: string;
  employeeName: string;
  startDate: string;
  endDate: string;
  leaveCategory: string;
  reason: string;
  status: 'Pending' | 'Approved' | 'Rejected' | 'Withdrawn';
}