import React, { useState } from 'react';
import { Button, Form, Input, DatePicker } from 'antd';
import { useAuth } from 'client/src/modules/auth/hooks/useAuth';
import { useLeaveTypes } from 'client/src/modules/leave/hooks/useLeaveTypes';

const LeaveRequestForm: React.FC = () => {
    const [form] = Form.useForm();
    const { user } = useAuth();
    const { leaveTypes } = useLeaveTypes();

    const onFinish = (values: any) => {
        const { leaveType, startDate, endDate } = values;
        submitLeaveApplication(user, leaveType, startDate, endDate);
    };

    return (
        <Form form={form} onFinish={onFinish}>
            <Form.Item name="leaveType" label="Leave Type" rules={[{ required: true }]}>
                <Input options={leaveTypes.map(type => ({ label: type.name, value: type.id }))} />
            </Form.Item>
            <Form.Item name="startDate" label="Start Date" rules={[{ required: true }]}>
                <DatePicker />
            </Form.Item>
            <Form.Item name="endDate" label="End Date" rules={[{ required: true }]}>
                <DatePicker />
            </Form.Item>
            <Form.Item>
                <Button type="primary" htmlType="submit">
                    Submit
                </Button>
            </Form.Item>
        </Form>
    );
};

export default LeaveRequestForm;
