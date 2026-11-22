import React, { useState } from "react";

export const LeaveManagementPage: React.FC = () => {
  const [leaveType, setLeaveType] = useState("Casual");
  const [days, setDays] = useState(1);
  const [reason, setReason] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>Leave Management</h1>
      <div style={{ background: "#fff", padding: 24, borderRadius: 8, marginBottom: 24 }}>
        <h3>Available Balances</h3>
        <p>Casual: 8 days | Restricted: 2 days | Medical: 15 days | Earned: 30 days</p>
      </div>
      <form onSubmit={handleSubmit} style={{ background: "#fff", padding: 24, borderRadius: 8 }}>
        <h3>Apply for Leave</h3>
        {submitted && <div style={{ color: "green", marginBottom: 12 }}>Leave application submitted successfully!</div>}
        <div style={{ marginBottom: 12 }}>
          <label>Leave Type: </label>
          <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
            <option value="Casual">Casual</option>
            <option value="Restricted">Restricted</option>
            <option value="Medical">Medical</option>
            <option value="Earned">Earned</option>
            <option value="Vacation">Vacation</option>
            <option value="Sabbatical">Sabbatical</option>
          </select>
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>Days: </label>
          <input type="number" min="1" value={days} onChange={(e) => setDays(Number(e.target.value))} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>Reason: </label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: "100%", height: 80 }} />
        </div>
        <button type="submit" style={{ padding: "8px 16px", background: "#0284c7", color: "#fff", border: "none", borderRadius: 4 }}>
          Submit Leave Request
        </button>
      </form>
    </div>
  );
};
export default LeaveManagementPage;
