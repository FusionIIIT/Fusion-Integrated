import React, { useState } from "react";

const LEAVE_TYPES = [
  { id: 1, name: "Casual Leave" },
  { id: 2, name: "Sick Leave" },
  { id: 3, name: "Earned Leave" },
];

interface ApplyLeaveForm {
  leaveType: number | "";
  startDate: string;
  endDate: string;
  reason: string;
}

const ApplyLeave: React.FC = () => {
  const [form, setForm] = useState<ApplyLeaveForm>({
    leaveType: "",
    startDate: "",
    endDate: "",
    reason: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch("/api/elm/leave-requests/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          leaveType: form.leaveType,   // mismatch: backend expects `leave_type`
          start_date: form.startDate,
          end_date: form.endDate,
          reason: form.reason,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(JSON.stringify(data));
        return;
      }
      setSubmitted(true);
    } catch (err) {
      setError("Network error. Please try again.");
    }
  };

  if (submitted) {
    return (
      <div style={{ padding: "2rem" }}>
        <h2>Leave application submitted successfully!</h2>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 480, margin: "2rem auto", padding: "1.5rem", border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>Apply for Leave</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "1rem" }}>
          <label>Leave Type</label>
          <select name="leaveType" value={form.leaveType} onChange={handleChange} required style={{ display: "block", width: "100%" }}>
            <option value="">-- Select --</option>
            {LEAVE_TYPES.map((lt) => (
              <option key={lt.id} value={lt.id}>
                {lt.name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label>Start Date</label>
          <input type="date" name="startDate" value={form.startDate} onChange={handleChange} required style={{ display: "block", width: "100%" }} />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label>End Date</label>
          <input type="date" name="endDate" value={form.endDate} onChange={handleChange} required style={{ display: "block", width: "100%" }} />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label>Reason</label>
          <textarea name="reason" value={form.reason} onChange={handleChange} rows={3} style={{ display: "block", width: "100%" }} />
        </div>
        <button type="submit">Submit Application</button>
      </form>
    </div>
  );
};

export default ApplyLeave;
