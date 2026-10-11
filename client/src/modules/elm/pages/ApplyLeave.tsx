import React, { useState } from 'react';

const ApplyLeave = () => {
  const [leaveData, setLeaveData] = useState({
    leaveType: '',
    startDate: '',
    endDate: '',
    reason: '',
  });

  const handleInputChange = (e) => {
    setLeaveData({
      ...leaveData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Send leaveData to backend using fetch or axios
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="leaveType">Leave Type:</label>
        <input
          type="text"
          id="leaveType"
          name="leaveType"
          value={leaveData.leaveType}
          onChange={handleInputChange}
        />
      </div>
      <div>
        <label htmlFor="startDate">Start Date:</label>
        <input
          type="date"
          id="startDate"
          name="startDate"
          value={leaveData.startDate}
          onChange={handleInputChange}
        />
      </div>
      <div>
        <label htmlFor="endDate">End Date:</label>
        <input
          type="date"
          id="endDate"
          name="endDate"
          value={leaveData.endDate}
          onChange={handleInputChange}
        />
      </div>
      <div>
        <label htmlFor="reason">Reason:</label>
        <textarea
          id="reason"
          name="reason"
          value={leaveData.reason}
          onChange={handleInputChange}
        />
      </div>
      <button type="submit">Apply for Leave</button>
    </form>
  );
};

export default ApplyLeave;