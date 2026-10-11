import React, { useState } from "react";
import { createLeaveApplication } from "./api";

export default function LeaveApplicationPage() {
  const [leaveTypeCode, setLeaveTypeCode] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [numberOfDays, setNumberOfDays] = useState(1);
  const [purpose, setPurpose] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [substituteId, setSubstituteId] = useState<number | undefined>(undefined);
  const [subDuties, setSubDuties] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createLeaveApplication({
        leave_type_code: leaveTypeCode,
        start_date: startDate,
        end_date: endDate,
        number_of_days: Number(numberOfDays),
        purpose,
        station_leave: stationLeave,
        substitute_id: substituteId ? Number(substituteId) : undefined,
        substitute_duties: subDuties,
      });
      setStatusMessage("Application submitted successfully!");
    } catch (err: any) {
      setStatusMessage(`Error: ${err.message}`);
    }
  };

  return (
    <div style={{ padding: "24px", maxWidth: "600px" }}>
      <h2>Submit Leave Application</h2>
      {statusMessage && <div style={{ marginBottom: "16px", padding: "8px", background: "#e7f5ff" }}>{statusMessage}</div>}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "12px" }}>
          <label>Leave Category: </label>
          <select value={leaveTypeCode} onChange={(e) => setLeaveTypeCode(e.target.value)}>
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="VL">Vacation Leave (VL)</option>
            <option value="COL">Commuted Leave (COL)</option>
          </select>
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>Start Date: </label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>End Date: </label>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>Number of Days: </label>
          <input type="number" step="0.5" value={numberOfDays} onChange={(e) => setNumberOfDays(Number(e.target.value))} required />
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>Station Leave Required: </label>
          <input type="checkbox" checked={stationLeave} onChange={(e) => setStationLeave(e.target.checked)} />
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>Purpose: </label>
          <textarea value={purpose} onChange={(e) => setPurpose(e.target.value)} rows={3} style={{ width: "100%" }} required />
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>Nominate Substitute (User ID): </label>
          <input type="number" value={substituteId || ""} onChange={(e) => setSubstituteId(Number(e.target.value))} />
        </div>
        <div style={{ marginBottom: "12px" }}>
          <label>Substitute Duties Description: </label>
          <input type="text" value={subDuties} onChange={(e) => setSubDuties(e.target.value)} style={{ width: "100%" }} />
        </div>
        <button type="submit" style={{ padding: "8px 16px", cursor: "pointer" }}>Submit Application</button>
      </form>
    </div>
  );
}
