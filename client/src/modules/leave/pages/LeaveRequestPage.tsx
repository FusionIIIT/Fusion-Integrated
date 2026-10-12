import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Form, Input, Select } from 'antd';
import { useCreateLeaveRequest } from 'client/src/modules/leave/hooks';

const { Option } = Select;

const LeaveRequestPage: React.FC = () => {
    const [form] = Form.useForm();
    const navigate = useNavigate();
    const createLeaveRequest = useCreateLeaveRequest();

    const onFinish = async (values: any) => {
        const { leave_type, start_date, end_date } = values;
        await createLeaveRequest(leave_type, start_date, end_date);
        navigate('/leave-requests');
    };

    return (
        <Form form={form} onFinish={onFinish}>
            <Form.Item name="leave_type" label="Leave Type" rules={[{ required: true }]}>
                <Select placeholder="Select a leave type">
                    <Option value="sick">Sick Leave</Option>
                    <Option value="annual">Annual Leave</Option>
                </Select>
            </Form.Item>
            <Form.Item name="start_date" label="Start Date" rules={[{ required: true }]}>
                <Input type="date" />
            </Form.Item>
            <Form.Item name="end_date" label="End Date" rules={[{ required: true }]}>
                <Input type="date" />
            </Form.Item>
            <Form.Item>
                <Button type="primary" htmlType="submit">
                    Submit
                </Button>
            </Form.Item>
        </Form>
    );
};

export default LeaveRequestPage;
