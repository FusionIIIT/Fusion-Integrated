import React, { useState } from 'react';

const LeaveApplication = () => {
  const [leaveType, setLeaveType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [substitute, setSubstitute] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    // handle form submission
  }

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Leave Type:
        <select value={leaveType} onChange={e =>
setLeaveType(e.target.value)}>
          <option value="">Select...</option>
          {/* populate options dynamically from available leave types
*/}
        </select>
      </label>
      <label>
        Start Date:
        <input type="date" value={startDate} onChange={e =>
setStartDate(e.target.value)} />
      </label>
      <label>
        End Date:
        <input type="date" value={endDate} onChange={e =>
setEndDate(e.target.value)} />
      </label>
      <label>
        Reason:
        <textarea value={reason} onChange={e =>
setReason(e.target.value)} />
      </label>
      <label>
        Substitute:
        <input type="text" value={substitute} onChange={e =>
setSubstitute(e.target.value)} />
      </label>
      <input type="submit" value="Submit" />
    </form>
  );
}

export default LeaveApplication;