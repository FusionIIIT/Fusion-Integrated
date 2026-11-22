import { useState, type FormEvent } from "react";
import { createLeaveApplication } from "../api";

export default function ApplyLeavePage() {
  const [leaveType, setLeaveType] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [reason, setReason] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [requiresStationLeave, setRequiresStationLeave] = useState(false);
  const [stationLeaveAddress, setStationLeaveAddress] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      await createLeaveApplication({
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        is_half_day: isHalfDay,
        reason,
        substitute_id: substituteId,
        requires_station_leave: requiresStationLeave,
        station_leave_address: stationLeaveAddress,
      });
      setMessage("Leave application submitted.");
    } catch (err: any) {
      setMessage(err.message || "Error submitting leave request.");
    }
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "600px" }}>
      <h2>Apply for Leave</h2>
      {message && <p>{message}</p>}
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <label>
          Leave Category:
          <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} style={{ marginLeft: "0.5rem" }}>
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="VL">Vacation Leave (VL)</option>
            <option value="COL">Commuted Leave (COL)</option>
          </select>
        </label>

        <label>
          Start Date:
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required style={{ marginLeft: "0.5rem" }} />
        </label>

        <label>
          End Date:
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required style={{ marginLeft: "0.5rem" }} />
        </label>

        <label>
          <input type="checkbox" checked={isHalfDay} onChange={(e) => setIsHalfDay(e.target.checked)} />
          Half-Day Leave (CL only)
        </label>

        <label>
          Substitute Employee ID:
          <input type="text" value={substituteId} onChange={(e) => setSubstituteId(e.target.value)} style={{ marginLeft: "0.5rem" }} />
        </label>

        <label>
          <input type="checkbox" checked={requiresStationLeave} onChange={(e) => setRequiresStationLeave(e.target.checked)} />
          Requires Station Leave
        </label>

        {requiresStationLeave && (
          <label>
            Outstation Address:
            <input type="text" value={stationLeaveAddress} onChange={(e) => setStationLeaveAddress(e.target.value)} style={{ marginLeft: "0.5rem", width: "100%" }} />
          </label>
        )}

        <label>
          Reason:
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} required rows={3} style={{ width: "100%" }} />
        </label>

        <button type="submit" style={{ padding: "0.5rem 1rem", width: "fit-content" }}>
          Submit Leave Request
        </button>
      </form>
    </div>
  );
}
