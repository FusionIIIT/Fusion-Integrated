import { type FormEvent, useState } from "react";

const LeaveApplication = () => {
  const [leaveType, setLeaveType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Handle form submission logic here
    console.log("Leave Type:", leaveType);
    console.log("Start Date:", startDate);
    console.log("End Date:", endDate);
    console.log("Reason:", reason);
  };

  return (
    <div>
      <h1>Leave Application</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="leaveType">Leave Type:</label>
          <select id="leaveType" value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
            <option value="CL">Casual Leave</option>
            <option value="RH">Recreational Holiday</option>
            <option value="SCL">Special Casual Leave</option>
            <option value="EL">Earned Leave</option>
            <option value="VL">Vacation Leave</option>
            <option value="COL">Compensatory Off Leave</option>
          </select>
        </div>
        <div>
          <label htmlFor="startDate">Start Date:</label>
          <input
            type="date"
            id="startDate"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="endDate">End Date:</label>
          <input
            type="date"
            id="endDate"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="reason">Reason:</label>
          <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)}></textarea>
        </div>
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default LeaveApplication;
