import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { submitLeave } from "../api/hooks";
import type { LeaveType } from "../api/types";

export function ApplyLeavePage() {
  const navigate = useNavigate();
  const [leaveType, setLeaveType] = useState<LeaveType>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [duration, setDuration] = useState("1");
  const [reason, setReason] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [session, setSession] = useState("FN");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [outFrom, setOutFrom] = useState("");
  const [outTo, setOutTo] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await submitLeave({
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        duration_days: parseFloat(duration),
        reason,
        is_half_day: isHalfDay,
        half_day_session: isHalfDay ? session : undefined,
        station_leave: stationLeave,
        station_leave_address: stationLeave ? stationAddress : undefined,
        out_of_station_from: stationLeave ? outFrom : undefined,
        out_of_station_to: stationLeave ? outTo : undefined,
        substitute_id: substituteId.trim() || undefined,
      });
      navigate("/elm/mine");
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.error || err.message || "Failed to submit leave request.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "1.5rem" }}>
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a formal leave request and station departure notification"
      />

      {errorMsg && (
        <div style={{ padding: "1rem", backgroundColor: "#fee2e2", color: "#b91c1c", borderRadius: 6, marginBottom: "1rem" }}>
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ background: "#ffffff", padding: "1.5rem", borderRadius: 8, border: "1px solid #e2e8f0" }}>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Leave Category</label>
          <select
            value={leaveType}
            onChange={(e) => setLeaveType(e.target.value as LeaveType)}
            style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1" }}
          >
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="COL">Commuted Leave (COL)</option>
            <option value="VL">Vacation Leave (VL)</option>
          </select>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
          <div>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Start Date</label>
            <input
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>End Date</label>
            <input
              type="date"
              required
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1" }}
            />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
          <div>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Duration (Days)</label>
            <input
              type="number"
              step="0.5"
              min="0.5"
              required
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Substitute Employee ID / Username</label>
            <input
              type="text"
              placeholder="e.g. fac_cs_02"
              value={substituteId}
              onChange={(e) => setSubstituteId(e.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1" }}
            />
          </div>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={stationLeave}
              onChange={(e) => setStationLeave(e.target.checked)}
            />
            <span style={{ fontWeight: 600 }}>Availing Station Leave (Leaving Jabalpur)</span>
          </label>
          {stationLeave && (
            <div style={{ marginTop: 8, padding: 12, backgroundColor: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Contact Address / Out-of-station Destination</label>
              <textarea
                rows={2}
                required={stationLeave}
                value={stationAddress}
                onChange={(e) => setStationAddress(e.target.value)}
                placeholder="Address and contact details during absence"
                style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1", marginBottom: 8 }}
              />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: 12 }}>Depart Jabalpur</label>
                  <input
                    type="date"
                    value={outFrom}
                    onChange={(e) => setOutFrom(e.target.value)}
                    style={{ width: "100%", padding: 6, borderRadius: 4, border: "1px solid #cbd5e1" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 12 }}>Return to Jabalpur</label>
                  <input
                    type="date"
                    value={outTo}
                    onChange={(e) => setOutTo(e.target.value)}
                    style={{ width: "100%", padding: 6, borderRadius: 4, border: "1px solid #cbd5e1" }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Reason for Leave</label>
          <textarea
            rows={3}
            required
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain grounds for leave request..."
            style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #cbd5e1" }}
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          style={{
            backgroundColor: "#2563eb",
            color: "#fff",
            padding: "0.6rem 1.5rem",
            borderRadius: 6,
            border: "none",
            fontWeight: 600,
            cursor: submitting ? "not-allowed" : "pointer",
          }}
        >
          {submitting ? "Submitting..." : "Submit Leave Application"}
        </button>
      </form>
    </div>
  );
}
