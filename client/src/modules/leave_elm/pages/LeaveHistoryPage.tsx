import React from 'react';
import { Table } from 'antd';
import moment from 'moment';

interface LeaveHistoryItem {
  id: number;
  employeeName: string;
  leaveType: string;
  reason: string;
  startDate: Date;
  endDate: Date;
  status: string;
}

const LeaveHistoryPage: React.FC = () => {
  const leaveHistoryData: LeaveHistoryItem[] = [
    // Example data
    { id: 1, employeeName: 'John Doe', leaveType: 'Casual Leave', reason: 'Personal reasons', startDate: new Date('2023-10-01'), endDate: new Date('2023-10-08'), status: 'Pending' },
    { id: 2, employeeName: 'Jane Smith', leaveType: 'Restricted Holiday', reason: 'Annual leave', startDate: new Date('2023-11-05'), endDate: new Date('2023-11-07'), status: 'Approved' },
    // Add more data as needed
  ];

  const columns = [
    {
      title: 'Employee Name',
      dataIndex: 'employeeName',
      key: 'employeeName',
    },
    {
      title: 'Leave Type',
      dataIndex: 'leaveType',
      key: 'leaveType',
    },
    {
      title: 'Reason',
      dataIndex: 'reason',
      key: 'reason',
    },
    {
      title: 'Start Date',
      dataIndex: 'startDate',
      key: 'startDate',
      render: (date) => moment(date).format('YYYY-MM-DD'),
    },
    {
      title: 'End Date',
      dataIndex: 'endDate',
      key: 'endDate',
      render: (date) => moment(date).format('YYYY-MM-DD'),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <span style={{ color: status === 'Pending' ? 'red' : 'green' }}>
          {status}
        </span>
      ),
    },
  ];

  return (
    <div className="leave-history-page">
      <h1>Leave History</h1>
      <Table columns={columns} dataSource={leaveHistoryData} />
    </div>
  );
};

export default LeaveHistoryPage;