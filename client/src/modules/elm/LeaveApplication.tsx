import { type FormEvent, useState } from "react";
import { submitLeaveApplication } from "./api";

const LeaveApplication = () => {
  const [leaveType, setLeaveType] = useState("1");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setFeedback(null);
    try {
      await submitLeaveApplication({
        leave_type: parseInt(leaveType, 10),
        start_date: startDate,
        end_date: endDate,
        reason,
      });
      setFeedback({ type: "success", message: "Leave application submitted successfully!" });
      setStartDate("");
      setEndDate("");
      setReason("");
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: err.response?.data?.detail || "Failed to submit leave application.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: "600px" }}>
      <h1>Apply for Leave</h1>

      {feedback && (
        <div
          style={{
            padding: "0.75rem",
            marginBottom: "1rem",
            borderRadius: "4px",
            backgroundColor: feedback.type === "success" ? "#e6ffed" : "#ffeef0",
            color: feedback.type === "success" ? "#1a7f37" : "#cf222e",
            border: `1px solid ${feedback.type === "success" ? "#a8f0b7" : "#ffc1c0"}`,
          }}
        >
          {feedback.message}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label htmlFor="leaveType">Leave Type:</label>
          <select
            id="leaveType"
            value={leaveType}
            onChange={(e) => setLeaveType(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
          >
            <option value="1">Casual Leave (CL)</option>
            <option value="2">Recreational Holiday (RH)</option>
            <option value="3">Special Casual Leave (SCL)</option>
            <option value="4">Earned Leave (EL)</option>
            <option value="5">Vacation Leave (VL)</option>
            <option value="6">Compensatory Off Leave (COL)</option>
          </select>
        </div>

        <div>
          <label htmlFor="startDate">Start Date:</label>
          <input
            type="date"
            id="startDate"
            required
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label htmlFor="endDate">End Date:</label>
          <input
            type="date"
            id="endDate"
            required
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label htmlFor="reason">Reason:</label>
          <textarea
            id="reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "0.75rem",
            backgroundColor: "#0969da",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Submitting..." : "Submit Application"}
        </button>
      </form>
    </div>
  );
};

export default LeaveApplication;
