import React, { useState, useEffect } from 'react';
import { LeaveType, LeaveRequest, LeaveBalance } from './types';

const LeaveDashboard: React.FC = () => {
  const [leaveBalances, setLeaveBalances] = useState<LeaveBalance[]>([]);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
  const [substituteRequests, setSubstituteRequests] = useState<LeaveRequest[]>([]);
  const [showApplyForm, setShowApplyForm] = useState(false);
  const [applyFormValues, setApplyFormValues] = useState({
    type: LeaveType.CL,
    startDate: '',
    endDate: '',
    halfDay: false,
  });

  useEffect(() => {
    // Fetch leave balances
    fetch('/api/leave-balances')
      .then(response => response.json())
      .then(data => setLeaveBalances(data));

    // Fetch current user's leave requests
    fetch('/api/leave-requests')
      .then(response => response.json())
      .then(data => setLeaveRequests(data));

    // Fetch substitute requests
    fetch('/api/substitute-requests')
      .then(response => response.json())
      .then(data => setSubstituteRequests(data));
  }, []);

  const handleApplyFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setApplyFormValues({
      ...applyFormValues,
      [e.target.name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value,
    });
  };

  const handleApplyFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Submit apply form logic here
    setShowApplyForm(false);
  };

  const handleWithdrawLeaveRequest = (requestId: string) => {
    // Withdraw leave request logic here
  };

  const handleAcceptSubstituteRequest = (requestId: string) => {
    // Accept substitute request logic here
  };

  const handleDeclineSubstituteRequest = (requestId: string) => {
    // Decline substitute request logic here
  };

  return (
    <div>
      <h1>Employee Leave Management (ELM)</h1>
      <div>
        {leaveBalances.map(balance => (
          <div key={balance.type}>
            <h2>{balance.type}</h2>
            <p>Balance: {balance.balance}</p>
            <p>Used: {balance.used}</p>
          </div>
        ))}
      </div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Dates</th>
            <th>Purpose</th>
            <th>Status</th>
            <th>Withdraw</th>
          </tr>
        </thead>
        <tbody>
          {leaveRequests.map(request => (
            <tr key={request.id}>
              <td>{request.id}</td>
              <td>{request.type}</td>
              <td>{request.dates}</td>
              <td>{request.purpose}</td>
              <td>
                <span className={`badge ${request.status}`}>{request.status}</span>
              </td>
              <td>
                <button onClick={() => handleWithdrawLeaveRequest(request.id)}>Withdraw</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={() => setShowApplyForm(true)}>Apply for Leave</button>
      {showApplyForm && (
        <div>
          <h2>Apply for Leave</h2>
          <form onSubmit={handleApplyFormSubmit}>
            <select name="type" value={applyFormValues.type} onChange={handleApplyFormChange}>
              <option value={LeaveType.CL}>Casual Leave</option>
              <option value={LeaveType.RH}>Restricted Holiday</option>
              <option value={LeaveType.EL}>Earned Leave</option>
            </select>
            <input
              type="date"
              name="startDate"
              value={applyFormValues.startDate}
              onChange={handleApplyFormChange}
            />
            <input
              type="date"
              name="endDate"
              value={applyFormValues.endDate}
              onChange={handleApplyFormChange}
            />
            <label>
              Half Day
              <input
                type="checkbox"
                name="halfDay"
                checked={applyFormValues.halfDay}
                onChange={handleApplyFormChange}
              />
            </label>
            <button type="submit">Submit</button>
          </form>
        </div>
      )}
      <h2>Substitute Requests</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Dates</th>
            <th>Purpose</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {substituteRequests.map(request => (
            <tr key={request.id}>
              <td>{request.id}</td>
              <td>{request.type}</td>
              <td>{request.dates}</td>
              <td>{request.purpose}</td>
              <td>
                <span className={`badge ${request.status}`}>{request.status}</span>
              </td>
              <td>
                <button onClick={() => handleAcceptSubstituteRequest(request.id)}>Accept</button>
                <button onClick={() => handleDeclineSubstituteRequest(request.id)}>Decline</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeaveDashboard;