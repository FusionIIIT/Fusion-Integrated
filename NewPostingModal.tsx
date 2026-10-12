import React, { useState } from 'react';
import { Button, DatePicker, Input, Select } from 'antd';

const { Option } = Select;

const NewPostingModal: React.FC = () => {
    const [closesAt, setClosesAt] = useState(new Date());

    const handleClosesAtChange = (value: Date) => {
        setClosesAt(value);
    };

    return (
        <div>
            <h2>New Posting</h2>
            <Input placeholder="Company Name" />
            <Select placeholder="Sector">
                <Option value="it">IT</Option>
                <Option value="core">Core</Option>
                <Option value="other">Other</Option>
            </Select>
            <DatePicker label="Applications close" value={closesAt} onChange={handleClosesAtChange} clearable minDate={new Date()} placeholder="Select a date and time" />
            <Button type="primary">Submit</Button>
        </div>
    );
};

export default NewPostingModal;
