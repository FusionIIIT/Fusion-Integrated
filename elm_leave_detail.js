// path/to/modules/elm/components/elm_leave_detail.js
import React from 'react';
import { Form, Input, DatePicker } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useElmLeaveService } from '../services';

const { RangePicker } = DatePicker;

const ElmLeaveDetail = ({ leaveRequest }) => {
  const [startDate, setStartDate] = useState(leaveRequest.startDate);
  const [endDate, setEndDate] = useState(leaveRequest.endDate);
  const [categoryId, setCategoryId] = useState(leaveRequest.categoryId);
  const [categoryIdOptions, setCategoryIdOptions] = useState([]);
  const navigate = useNavigate();
  const elmLeaveService = useElmLeaveService();

  const fetchLeaveCategories = async () => {
    const categories = await elmLeaveService.getLeaveCategories();
    setCategoryIdOptions(categories.map(category => ({ label: category.name, value: category.id })));
  };

  const handleSubmit = async () => {
    try {
      const updatedRequest = await elmLeaveService.updateLeaveRequest(
        leaveRequest.id,
        categoryId,
        startDate,
        endDate
      );
      navigate(`/leave/${updatedRequest.id}`);
    } catch (error) {
      alert(error.message);
    }
  };

  return (
    <Form onFinish={handleSubmit}>
      <Form.Item label="Leave Category" name="categoryId">
        <Select options={categoryIdOptions} />
      </Form.Item>
      <Form.Item label="Start Date" name="startDate">
        <RangePicker onChange={(dates) => setStartDate(dates)} />
      </Form.Item>
      <Form.Item label="End Date" name="endDate">
        <RangePicker onChange={(dates) => setEndDate(dates)} />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit">
          Update Leave Request
        </Button>
      </Form.Item>
    </Form>
  );
};

export default ElmLeaveDetail;
