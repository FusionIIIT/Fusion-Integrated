// path/to/modules/elm/components/elm_leave_form.js
import React, { useState } from 'react';
import { Button, Form, Input, DatePicker } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useElmLeaveService } from '../services';

const { RangePicker } = DatePicker;

const ElmLeaveForm = () => {
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [categoryId, setCategoryId] = useState('');
  const [categoryIdOptions, setCategoryIdOptions] = useState([]);
  const navigate = useNavigate();
  const elmLeaveService = useElmLeaveService();

  const fetchLeaveCategories = async () => {
    const categories = await elmLeaveService.getLeaveCategories();
    setCategoryIdOptions(categories.map(category => ({ label: category.name, value: category.id })));
  };

  const handleSubmit = async () => {
    try {
      const leaveRequest = await elmLeaveService.applyForLeave(
        localStorage.getItem('userId'),
        categoryId,
        startDate,
        endDate
      );
      navigate(`/leave/${leaveRequest.id}`);
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
          Apply for Leave
        </Button>
      </Form.Item>
    </Form>
  );
};

export default ElmLeaveForm;
