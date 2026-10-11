import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Table, Pagination } from 'antd';

interface LeaveApplication {
  id: number;
  employeeName: string;
  leaveType: string;
  startDate: Date;
  endDate: Date;
  status: string;
}

const LeaveApprovalsPage: React.FC = () => {
  const navigate = useNavigate();

  // Mock data for leave applications
  const leaveApplications: LeaveApplication[] = [
    { id: 1, employeeName: 'John Doe', leaveType: 'Casual Leave', startDate: new Date('2023-10-01'), endDate: new Date('2023-10-05'), status: 'Pending' },
    { id: 2, employeeName: 'Jane Smith', leaveType: 'Restricted Holiday', startDate: new Date('2023-10-10'), endDate: new Date('2023-10-12'), status: 'Pending' },
    // Add more leave applications as needed
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
      title: 'Start Date',
      dataIndex: 'startDate',
      key: 'startDate',
      render: (date: Date) => date.toLocaleDateString(),
    },
    {
      title: 'End Date',
      dataIndex: 'endDate',
      key: 'endDate',
      render: (date: Date) => date.toLocaleDateString(),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
    },
    {
      title: 'Actions',
      dataIndex: '',
      key: 'actions',
      render: (_, record) => (
        <Button type="primary" onClick={() => navigate(`/leave/apply/${record.id}`)}>Approve</Button>
        <Button danger onClick={() => console.log('Reject')}>Reject</Button>
      ),
    },
  ];

  const [currentPage, setCurrentPage] = React.useState(1);
  const pageSize = 5;

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <div className="leave-approvals-page">
      <h2>Leave Approvals</h2>
      <Table
        columns={columns}
        dataSource={leaveApplications.slice((currentPage - 1) * pageSize, currentPage * pageSize)}
        pagination={{
          total: leaveApplications.length,
          current: currentPage,
          pageSize,
          onChange: handlePageChange,
        }}
      />
    </div>
  );
};

export default LeaveApprovalsPage;