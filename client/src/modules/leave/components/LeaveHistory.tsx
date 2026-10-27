import React, { useEffect, useState } from 'react';
import { useAuth } from 'client/src/modules/auth/hooks/useAuth';
import { useLeaveApplications } from 'client/src/modules/leave/hooks/useLeaveApplications';

const LeaveHistory: React.FC = () => {
    const { user } = useAuth();
    const { leaveApplications } = useLeaveApplications(user);

    return (
        <div>
            <h2>Leave History</h2>
            <ul>
                {leaveApplications.map(application => (
                    <li key={application.id}>
                        {application.leave_type.name} - {application.start_date} to {application.end_date} - {application.status}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default LeaveHistory;
