import React from 'react';
import { Button, Dropdown, Menu } from 'antd';

const PageHeader: React.FC = ({ title, subtitle, action }) => {
    const menu = (
        <Menu>
            <Menu.Item key="1">Profile</Menu.Item>
            <Menu.Item key="2">Settings</Menu.Item>
            <Menu.Item key="3">Logout</Menu.Item>
        </Menu>
    );

    return (
        <div>
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
            {action && <Button>{action}</Button>}
            <Dropdown overlay={menu} trigger={['click']}>
                <Button>Menu</Button>
            </Dropdown>
        </div>
    );
};

export default PageHeader;
