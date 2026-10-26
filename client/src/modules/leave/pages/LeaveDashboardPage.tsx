import React, { useEffect, useState } from "react";
import { leaveApi, LeaveBalance, LeaveApplication } from "../api/leaveApi";

export default function LeaveDashboardPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Default test user EMP101
  const userId = "EMP101";

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    setLoading(true);
    try {
      const [bals, apps] = await Promise.all([
        leaveApi.getBalances(userId, 2026),
        leaveApi.getApplications({ applicant_id: userId })
      ]);
      setBalances(bals);
      setApplications(apps);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleWithdraw(appId: number) {
    if (!window.confirm("Are you sure you want to withdraw this pending request?")) return;
    try {
      await leaveApi.withdraw({ applicant_id: userId, application_id: appId });
      loadDashboard();
    } catch (err: any) {
      alert(err.message || "Failed to withdraw");
    }
  }

  if (loading) {
    return <div style={{ padding: "2rem" }}>Loading ELM Dashboard...</div>;
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>Employee Leave Management (ELM) — Dashboard</h2>

      {/* Balances Section */}
      <h3 style={{ marginTop: "1.5rem" }}>Current Leave Balances (2026)</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "1rem" }}>
        {balances.length === 0 ? (
          <p>No leave balances found for current year.</p>
        ) : (
          balances.map((b) => (
            <div key={b.category} style={{ border: "1px solid #ccc", borderRadius: "8px", padding: "1rem", backgroundColor: "#f9f9f9" }}>
              <div style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#0066cc" }}>{b.category}</div>
              <div style={{ margin: "0.5rem 0", fontSize: "1.5rem", fontWeight: "bold" }}>{b.balance} days</div>
              <div style={{ fontSize: "0.85rem", color: "#666" }}>
                Availed: {b.availed} | Pending: {b.pending}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Action Buttons */}
      <div style={{ margin: "2rem 0" }}>
        <a href="/leave/apply" style={{ padding: "0.75rem 1.5rem", backgroundColor: "#0066cc", color: "#fff", textDecoration: "none", borderRadius: "4px", marginRight: "1rem" }}>
          + Apply for Leave
        </a>
        <a href="/leave/substitute-inbox" style={{ padding: "0.75rem 1.5rem", backgroundColor: "#6c757d", color: "#fff", textDecoration: "none", borderRadius: "4px", marginRight: "1rem" }}>
          Substitute Inbox
        </a>
        <a href="/leave/approvals" style={{ padding: "0.75rem 1.5rem", backgroundColor: "#28a745", color: "#fff", textDecoration: "none", borderRadius: "4px" }}>
          Approval Queue
        </a>
      </div>

      {/* Applications List */}
      <h3>My Leave Applications</h3>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem" }}>
        <thead>
          <tr style={{ backgroundColor: "#eaeaea", textAlign: "left" }}>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>App ID</th>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>Category</th>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>Period</th>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>Days</th>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>Status</th>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>Current Authority</th>
            <th style={{ padding: "0.5rem", border: "1px solid #ccc" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {applications.length === 0 ? (
            <tr><td colSpan={7} style={{ padding: "1rem", textAlign: "center" }}>No leave applications submitted yet.</td></tr>
          ) : (
            applications.map((app) => (
              <tr key={app.id}>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>#{app.id}</td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}><strong>{app.category}</strong></td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>{app.start_date} to {app.end_date}</td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>{app.requested_days}</td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>
                  <span style={{
                    padding: "0.25rem 0.5rem",
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                    backgroundColor: app.status === "APPROVED" ? "#d4edda" : app.status === "REJECTED" ? "#f8d7da" : "#fff3cd",
                    color: app.status === "APPROVED" ? "#155724" : app.status === "REJECTED" ? "#721c24" : "#856404"
                  }}>
                    {app.status}
                  </span>
                </td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>{app.current_authority_role}</td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>
                  {["AWAITING_SUBSTITUTE", "AWAITING_UNIT_HEAD", "AWAITING_ESTABLISHMENT", "AWAITING_FINAL_SANCTION"].includes(app.status) && (
                    <button onClick={() => handleWithdraw(app.id)} style={{ padding: "0.25rem 0.5rem", backgroundColor: "#dc3545", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                      Withdraw
                    </button>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
