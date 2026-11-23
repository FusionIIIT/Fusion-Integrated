import React, { useEffect, useState } from 'react';
import { fetchLeaveBalances, fetchLeaveApplications, LeaveBalance, LeaveApplication } from '../api/leaveApi';

export const LeaveDashboard: React.FC = () => {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [leaves, setLeaves] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchLeaveBalances(), fetchLeaveApplications()])
      .then(([balanceData, leaveData]) => {
        setBalances(balanceData);
        setLeaves(leaveData);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading Leave Management...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Employee Leave Management (ELM)</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {balances.map((b) => (
          <div key={b.id} className="p-4 bg-white shadow rounded-lg border">
            <h3 className="text-sm font-medium text-gray-500">Leave Type ID: {b.leave_type}</h3>
            <p className="text-3xl font-semibold mt-1">{b.balance} Days</p>
          </div>
        ))}
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">My Leave Applications</h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Start Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">End Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {leaves.map((l, idx) => (
              <tr key={idx}>
                <td className="px-6 py-4 whitespace-nowrap">{l.leave_type}</td>
                <td className="px-6 py-4 whitespace-nowrap">{l.start_date}</td>
                <td className="px-6 py-4 whitespace-nowrap">{l.end_date}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs font-semibold rounded bg-yellow-100 text-yellow-800">
                    {l.status || 'Pending'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeaveDashboard;