import React, { useEffect, useState } from 'react';
import {
  fetchLeaveBalances,
  fetchLeaveApplications,
  fetchLeaveTypes,
  createLeaveApplication,
  withdrawLeaveApplication
} from '../api';
import type {
  LeaveBalance,
  LeaveApplication,
  LeaveType
} from '../api';

export const LeaveDashboard: React.FC = () => {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [leaves, setLeaves] = useState<LeaveApplication[]>([]);
  const [types, setTypes] = useState<LeaveType[]>([]);
  const [loading, setLoading] = useState(true);

  // Form Modal state
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState<LeaveApplication>({
    leave_type: 1,
    start_date: '',
    end_date: '',
    half_day: 'NONE',
    reason: '',
    is_station_leave: false,
    station_leave_address: '',
  });

  const loadData = () => {
    setLoading(true);
    Promise.all([fetchLeaveBalances(), fetchLeaveApplications(), fetchLeaveTypes()])
      .then(([balanceData, leaveData, typeData]) => {
        setBalances(balanceData);
        setLeaves(leaveData);
        setTypes(typeData);

        const firstType = typeData[0];
        if (firstType && firstType.id !== undefined) {
          setFormData((prev) => ({ ...prev, leave_type: firstType.id }));
        }
      })
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    loadData();
  }, []);

  const handleWithdraw = async (id?: number) => {
    if (!id) return;
    if (window.confirm('Are you sure you want to withdraw this pending leave application?')) {
      try {
        await withdrawLeaveApplication(id);
        alert('Leave application withdrawn.');
        loadData();
      } catch (err) {
        alert('Failed to withdraw leave application.');
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createLeaveApplication(formData);
      alert('Leave application submitted successfully!');
      setShowModal(false);
      loadData();
    } catch (err) {
      alert('Error submitting leave application.');
    }
  };

  if (loading) return <div className="p-6">Loading Leave Management...</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Employee Leave Management (ELM)</h1>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          + Apply for Leave
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {balances.map((b) => (
          <div key={b.id} className="p-4 bg-white shadow rounded-lg border">
            <h3 className="text-sm font-medium text-gray-500">{b.leave_type_name || `Leave Type ID: ${b.leave_type}`}</h3>
            <p className="text-3xl font-semibold mt-1 text-blue-600">{b.balance} Days</p>
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {leaves.map((l, idx) => (
              <tr key={l.id || idx}>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{l.leave_type_code || l.leave_type}</td>
                <td className="px-6 py-4 whitespace-nowrap">{l.start_date}</td>
                <td className="px-6 py-4 whitespace-nowrap">{l.end_date}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded ${l.status === 'Approved' ? 'bg-green-100 text-green-800' :
                    l.status === 'Rejected' ? 'bg-red-100 text-red-800' :
                      l.status === 'Withdrawn' ? 'bg-gray-100 text-gray-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                    {l.status || 'Pending'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {l.status && !['Approved', 'Rejected', 'Withdrawn', 'Cancelled'].includes(l.status) && (
                    <button
                      onClick={() => handleWithdraw(l.id)}
                      className="text-red-600 hover:text-red-800 font-medium text-xs"
                    >
                      Withdraw
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-lg font-bold">New Leave Application</h3>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-sm font-medium">Leave Type</label>
                <select
                  value={formData.leave_type}
                  onChange={(e) => setFormData({ ...formData, leave_type: Number(e.target.value) })}
                  className="w-full border p-2 rounded mt-1"
                >
                  {types.map((t) => (
                    <option key={t.id} value={t.id}>{t.code} - {t.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-sm font-medium">Start Date</label>
                  <input
                    type="date"
                    required
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full border p-2 rounded mt-1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">End Date</label>
                  <input
                    type="date"
                    required
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full border p-2 rounded mt-1"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium">Reason</label>
                <textarea
                  required
                  rows={2}
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  className="w-full border p-2 rounded mt-1"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border rounded text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Submit Application
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeaveDashboard;