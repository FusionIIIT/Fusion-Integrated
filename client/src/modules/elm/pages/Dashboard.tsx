import React, { useEffect, useState } from "react";
import { fetchBalances, fetchRequests, LeaveBalance, LeaveRequest } from "../api/client";

export default function LeaveDashboard() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchBalances(), fetchRequests()])
      .then(([b, r]) => {
        setBalances(b);
        setRequests(r);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "24px", fontWeight: "bold", marginBottom: "20px" }}>Employee Leave Management</h1>
      
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "12px" }}>Leave Balances</h2>
        {loading ? (
          <p>Loading balances...</p>
        ) : balances.length === 0 ? (
          <p>No active leave balances found for current year.</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
            {balances.map((b) => (
              <div key={b.id} style={{ border: "1px solid #e2e8f0", borderRadius: "8px", padding: "16px", background: "#f8fafc" }}>
                <div style={{ fontWeight: "600", fontSize: "16px", color: "#334155" }}>{b.leave_type}</div>
                <div style={{ fontSize: "24px", fontWeight: "bold", color: "#0f172a", marginTop: "8px" }}>{b.balance}</div>
                <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>Allocated: {b.allocated} | Availed: {b.availed}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "12px" }}>Recent Leave Applications</h2>
        {loading ? (
          <p>Loading requests...</p>
        ) : requests.length === 0 ? (
          <p>No leave requests found.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #cbd5e1" }}>
                <th style={{ padding: "8px" }}>Type</th>
                <th style={{ padding: "8px" }}>Dates</th>
                <th style={{ padding: "8px" }}>Purpose</th>
                <th style={{ padding: "8px" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <td style={{ padding: "8px", fontWeight: "500" }}>{r.leave_type}</td>
                  <td style={{ padding: "8px" }}>{r.start_date} to {r.end_date}</td>
                  <td style={{ padding: "8px" }}>{r.purpose}</td>
                  <td style={{ padding: "8px" }}>
                    <span style={{
                      padding: "4px 8px",
                      borderRadius: "4px",
                      fontSize: "12px",
                      fontWeight: "600",
                      background: r.status === "APPROVED" ? "#dcfce7" : r.status === "REJECTED" ? "#fee2e2" : "#fef9c3",
                      color: r.status === "APPROVED" ? "#166534" : r.status === "REJECTED" ? "#991b1b" : "#854d0e"
                    }}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
