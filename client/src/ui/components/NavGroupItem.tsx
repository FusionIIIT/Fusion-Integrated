import React from 'react';

const NavGroupItem: React.FC<{ label: string, icon: string, to: string }> = ({ label, icon, to }) => {
    return (
        <a href={to}>
            <span>{icon}</span>
            <span>{label}</span>
        </a>
    );
};

export default NavGroupItem;
