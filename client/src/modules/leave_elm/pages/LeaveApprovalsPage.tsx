import React, { useState, useEffect } from 'react';
import { useAppDispatch } from '../../store';
import { getPendingLeaveApplications } from '../../../api/leaveApi';
import { LeaveApplicationType } from '../../../types/leave';
import {
  approveLeave,
  rejectLeave,
} from '../../../store/leaveSlice';
import { makeStyles } from '@mui/styles';

interface LeaveApprovalsPageProps {
  match: any;
}

const useStyles = makeStyles(() => ({
  container: {
    maxWidth: 1200px,
    margin: '0 auto',
    padding: '20px',
  },
  table: {
    minWidth: 600px,
    boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
  },
  tableHeader: {
    backgroundColor: '#f2f2f2',
    padding: '8px',
    textAlign: 'center',
  },
  tableRow: {
    padding: '8px',
    borderBottom: '1px solid #ddd',
  },
  tableCell: {
    padding: '8px',
  },
  button: {
    marginRight: '10px',
    padding: '8px 16px',
    fontSize: '14px',
    cursor: 'pointer',
    '&:disabled': {
      color: '#ccc',
      cursor: 'not-allowed',
    },
  },
}));

const LeaveApprovalsPage: React.FC<LeaveApprovalsPageProps> = ({ match }) => {
  const dispatch = useAppDispatch();
  const classes = useStyles();
  const [leaveApplications, setLeaveApplications] = useState<LeaveApplicationType[]>([]);

  useEffect(() => {
    const fetchLeaveApplications = async () => {
      try {
        const response = await getPendingLeaveApplications();
        setLeaveApplications(response);
      } catch (error) {
        console.error('Error fetching leave applications:', error);
      }
    };

    fetchLeaveApplications();
  }, [dispatch]);

  const handleApprove = async (id: string) => {
    try {
      await dispatch(approveLeave(id));
    } catch (error) {
      console.error('Error approving leave:', error);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await dispatch(rejectLeave(id));
    } catch (error) {
      console.error('Error rejecting leave:', error);
    }
  };

  return (
    <div className={classes.container}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Pending Leave Applications</h2>
      <div style={{ tableLayout: 'fixed' }}>
        <table className={classes.table}>
          <thead className={classes.tableHeader}>
            <tr>
              <th style={{ border: 'none', padding: '8px', textAlign: 'left' }}>Application ID</th>
              <th style={{ border: 'none', padding: '8px', textAlign: 'left' }}>Employee Name</th>
              <th style={{ border: 'none', padding: '8px', textAlign: 'left' }}>Leave Category</th>
              <th style={{ border: 'none', padding: '8px', textAlign: 'left' }}>Start Date</th>
              <th style={{ border: 'none', padding: '8px', textAlign: 'left' }}>End Date</th>
              <th style={{ border: 'none', padding: '8px', textAlign: 'left' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {leaveApplications.map((application) => (
              <tr key={application.id} className={classes.tableRow}>
                <td className={classes.tableCell}>{application.employeeId}</td>
                <td className={classes.tableCell}>{application.employeeName}</td>
                <td className={classes.tableCell}>{application.leaveCategory}</td>
                <td className={classes.tableCell}>{application.startDate}</td>
                <td className={classes.tableCell}>{application.endDate}</td>
                <td className={classes.tableCell}>Pending</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <button className={classes.button} onClick={() => handleApprove(leaveApplications[0].id)} disabled={!leaveApplications || leaveApplications.length === 0}>Approve</button>
        <button className={classes.button} onClick={() => handleReject(leaveApplications[0].id)} disabled={!leaveApplications || leaveApplications.length === 0}>Reject</button>
      </div>
    </div>
  );
};

export default LeaveApprovalsPage;