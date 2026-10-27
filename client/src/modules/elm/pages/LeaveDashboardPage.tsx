import { useEffect, useState } from "react";
import {
  cancelLeaveApplication,
  extendLeaveApplication,
  fetchMyApplications,
  fetchMyBalances,
  submitResumption,
  withdrawLeaveApplication,
  type LeaveApplication,
  type LeaveBalance,
} from "../api";

export default function LeaveDashboardPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [error, setError] = useState<string>("");
  const [message, setMessage] = useState<string>("");

  // Extension modal state
  const [extendingId, setExtendingId] = useState<number | null>(null);
  const [extEndDate, setExtEndDate] = useState<string>("");
  const [extReason, setExtReason] = useState<string>("");

  // Resumption modal state
  const [resumingId, setResumingId] = useState<number | null>(null);
  const [resumptionDate, setResumptionDate] = useState<string>("");
  const [resumptionRemarks, setResumptionRemarks] = useState<string>("");

  function loadData() {
    Promise.all([fetchMyBalances(), fetchMyApplications()])
      .then(([balData, appData]) => {
        setBalances(balData);
        setApplications(appData);
      })
      .catch((err) => setError(err.message || "Could not load leave data"));
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleWithdraw(id: number) {
    if (!window.confirm("Are you sure you want to withdraw this leave application?")) return;
    try {
      await withdrawLeaveApplication(id, "Withdrawn by applicant");
      setMessage("Leave application withdrawn successfully.");
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleCancel(id: number) {
    const reason = window.prompt("Reason for cancelling approved leave:") || "Personal reasons";
    try {
      await cancelLeaveApplication(id, reason);
      setMessage("Approved leave cancelled and balance restored.");
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleExtendSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!extendingId) return;
    try {
      await extendLeaveApplication(extendingId, extEndDate, extReason);
      setMessage("Leave extension application submitted.");
      setExtendingId(null);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleResumptionSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!resumingId) return;
    try {
      await submitResumption(resumingId, resumptionDate, resumptionRemarks);
      setMessage("Duty resumption submitted and unused balance restored.");
      setResumingId(null);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1100px", margin: "0 auto" }}>
      <h2>Employee Leave Dashboard</h2>
      {message && <div style={{ background: "#e6ffed", color: "#137333", padding: "0.75rem", borderRadius: "4px", marginBottom: "1rem" }}>{message}</div>}
      {error && <div style={{ background: "#fde8e8", color: "#c5221f", padding: "0.75rem", borderRadius: "4px", marginBottom: "1rem" }}>{error}</div>}

      <h3>My Leave Balances ({new Date().getFullYear()})</h3>
      <table border={1} cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginBottom: "2rem" }}>
        <thead style={{ background: "#f1f3f4" }}>
          <tr>
            <th>Leave Type</th>
            <th>Year</th>
            <th>Allocated</th>
            <th>Carried Fwd</th>
            <th>Used</th>
            <th>Available</th>
          </tr>
        </thead>
        <tbody>
          {balances.map((b) => (
            <tr key={b.id}>
              <td><strong>{b.leave_type}</strong></td>
              <td>{b.year}</td>
              <td>{b.total_allocated}</td>
              <td>{b.carried_forward}</td>
              <td>{b.used_days}</td>
              <td><strong style={{ color: "#137333" }}>{b.remaining_days}</strong></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>My Leave Applications & History</h3>
      <table border={1} cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead style={{ background: "#f1f3f4" }}>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Dates</th>
            <th>Days</th>
            <th>Status</th>
            <th>Substitute</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {applications.map((app) => {
            const canWithdraw = [
              "AWAITING_SUBSTITUTE",
              "SUBSTITUTE_DECLINED",
              "AWAITING_UNIT_HEAD",
              "AWAITING_SANCTION",
              "AWAITING_DIRECTOR_SELF_SANCTION",
            ].includes(app.status);
            const isApproved = app.status === "APPROVED";
            const canExtend = isApproved && ["EL", "COL", "VL"].includes(app.leave_type);

            return (
              <tr key={app.id}>
                <td>#{app.id} {app.is_extension ? "(Ext)" : ""}</td>
                <td>{app.leave_type}</td>
                <td>{app.start_date} to {app.end_date}</td>
                <td>{app.total_days} {app.is_half_day ? "(Half Day)" : ""}</td>
                <td>
                  <span style={{
                    padding: "0.25rem 0.5rem",
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                    background: isApproved ? "#e6ffed" : app.status === "REJECTED" ? "#fde8e8" : "#fef7e0",
                    color: isApproved ? "#137333" : app.status === "REJECTED" ? "#c5221f" : "#b06000",
                  }}>
                    {app.status}
                  </span>
                </td>
                <td>{app.substitute_id ? `${app.substitute_id} (${app.substitute_status})` : "-"}</td>
                <td>
                  {canWithdraw && (
                    <button onClick={() => handleWithdraw(app.id)} style={{ marginRight: "0.3rem" }}>
                      Withdraw
                    </button>
                  )}
                  {isApproved && (
                    <>
                      <button onClick={() => handleCancel(app.id)} style={{ marginRight: "0.3rem" }}>
                        Cancel
                      </button>
                      {canExtend && (
                        <button onClick={() => { setExtendingId(app.id); setExtEndDate(""); setExtReason(""); }} style={{ marginRight: "0.3rem" }}>
                          Extend
                        </button>
                      )}
                      <button onClick={() => { setResumingId(app.id); setResumptionDate(""); setResumptionRemarks(""); }}>
                        Resume Duty
                      </button>
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Extension Modal */}
      {extendingId && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#fff", padding: "1.5rem", borderRadius: "8px", width: "420px" }}>
            <h4>Extend Leave Application #{extendingId}</h4>
            <form onSubmit={handleExtendSubmit}>
              <label style={{ display: "block", marginBottom: "0.75rem" }}>
                New End Date:
                <input type="date" value={extEndDate} onChange={(e) => setExtEndDate(e.target.value)} required style={{ display: "block", width: "100%", marginTop: "0.25rem" }} />
              </label>
              <label style={{ display: "block", marginBottom: "0.75rem" }}>
                Reason for Extension:
                <textarea value={extReason} onChange={(e) => setExtReason(e.target.value)} required rows={3} style={{ display: "block", width: "100%", marginTop: "0.25rem" }} />
              </label>
              <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                <button type="button" onClick={() => setExtendingId(null)}>Cancel</button>
                <button type="submit">Submit Extension</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resumption Modal */}
      {resumingId && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#fff", padding: "1.5rem", borderRadius: "8px", width: "420px" }}>
            <h4>Duty Resumption for Leave #{resumingId}</h4>
            <form onSubmit={handleResumptionSubmit}>
              <label style={{ display: "block", marginBottom: "0.75rem" }}>
                Actual Resumption Date:
                <input type="date" value={resumptionDate} onChange={(e) => setResumptionDate(e.target.value)} required style={{ display: "block", width: "100%", marginTop: "0.25rem" }} />
              </label>
              <label style={{ display: "block", marginBottom: "0.75rem" }}>
                Remarks:
                <textarea value={resumptionRemarks} onChange={(e) => setResumptionRemarks(e.target.value)} rows={2} style={{ display: "block", width: "100%", marginTop: "0.25rem" }} />
              </label>
              <p style={{ fontSize: "0.85rem", color: "#555" }}>
                * If returning earlier than approved end date, unused leave days will be automatically restored to your balance.
              </p>
              <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                <button type="button" onClick={() => setResumingId(null)}>Cancel</button>
                <button type="submit">Submit Resumption</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
