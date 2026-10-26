import React, { useState } from "react";
import { submitLeave } from "../api/client";

export default function ApplyLeave() {
  const [leaveType, setLeaveType] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [purpose, setPurpose] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayPeriod] = useState("FIRST_HALF");
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      await submitLeave({
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        purpose,
        is_half_day: isHalfDay,
        half_day_period: isHalfDay ? halfDayPeriod : null,
        is_station_leave: isStationLeave,
        station_details: isStationLeave ? stationDetails : null,
      });
      setMessage({ type: "success", text: "Leave application submitted successfully!" });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to submit application." });
    }
  };

  return (
    <div style={{ padding: "24px", maxWidth: "600px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "24px", fontWeight: "bold", marginBottom: "20px" }}>Apply for Leave</h1>
      {message && (
        <div style={{
          padding: "12px",
          marginBottom: "16px",
          borderRadius: "6px",
          background: message.type === "success" ? "#dcfce7" : "#fee2e2",
          color: message.type === "success" ? "#166534" : "#991b1b",
        }}>
          {message.text}
        </div>
      )}
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div>
          <label style={{ display: "block", marginBottom: "4px", fontWeight: "500" }}>Leave Type</label>
          <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #cbd5e1" }}>
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="COL">Commuted Leave (COL)</option>
            <option value="VL">Vacation Leave (VL)</option>
          </select>
        </div>
        <div style={{ display: "flex", gap: "16px" }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: "4px", fontWeight: "500" }}>Start Date</label>
            <input type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #cbd5e1" }} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: "4px", fontWeight: "500" }}>End Date</label>
            <input type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #cbd5e1" }} />
          </div>
        </div>
        <div>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
            <input type="checkbox" checked={isHalfDay} onChange={(e) => setIsHalfDay(e.target.checked)} />
            Half Day (CL only)
          </label>
        </div>
        <div>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
            <input type="checkbox" checked={isStationLeave} onChange={(e) => setIsStationLeave(e.target.checked)} />
            Station Leave (Leaving Headquarters)
          </label>
        </div>
        {isStationLeave && (
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontWeight: "500" }}>Station Details / Contact Address</label>
            <textarea rows={2} value={stationDetails} onChange={(e) => setStationDetails(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #cbd5e1" }} />
          </div>
        )}
        <div>
          <label style={{ display: "block", marginBottom: "4px", fontWeight: "500" }}>Purpose / Reason</label>
          <textarea required rows={3} value={purpose} onChange={(e) => setPurpose(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #cbd5e1" }} />
        </div>
        <button type="submit" style={{ padding: "10px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "4px", fontWeight: "600", cursor: "pointer" }}>
          Submit Application
        </button>
      </form>
    </div>
  );
}
