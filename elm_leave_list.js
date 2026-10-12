// path/to/modules/elm/components/elm_leave_list.js
import React from 'react';
import { Table, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useElmLeaveService } from '../services';

const columns = [
  {
    title: 'Employee',
    dataIndex: 'employeeName',
    key: 'employeeName',
  },
  {
    title: 'Category',
    dataIndex: 'categoryName',
    key: 'categoryName',
  },
  {
    title: 'Start Date',
    dataIndex: 'startDate',
    key: 'startDate',
  },
  {
    title: 'End Date',
    dataIndex: 'endDate',
    key: 'endDate',
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: 'Action',
    dataIndex: 'action',
    key: 'action',
    render: (text, record) => (
      <Button type="link" onClick={() => navigate(`/leave/${record.id}`)}>
        View
      </Button>
    ),
  },
];

const ElmLeaveList = () => {
  const [leaveRequests, setLeaveRequests] = useState([]);
  const navigate = useNavigate();
  const elmLeaveService = useElmLeaveService();

  const fetchLeaveRequests = async () => {
    const requests = await elmLeaveService.getLeaveRequests(localStorage.getItem('userId'));
    setLeaveRequests(requests.map(request => ({
      id: request.id,
      employeeName: request.employee.name,
      categoryName: request.category.name,
      startDate: request.startDate.toISOString().split('T')[0],
      endDate: request.endDate.toISOString().split('T')[0],
      status: request.status,
    })));
  };

  React.useEffect(() => {
    fetchLeaveRequests();
  }, []);

  return (
    <Table columns={columns} dataSource={leaveRequests} />
  );
};

export default ElmLeaveList;
