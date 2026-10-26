import React, { useEffect, useState } from "react";
import { leaveApi, LeaveApplication } from "../api/leaveApi";

export default function SubstituteInboxPage() {
  const [requests, setRequests] = useState<LeaveApplication[]>([]);
  const [remarks, setRemarks] = useState<string>("");
  const substituteId = "EMP102"; // Test substitute Prof. Jones

  useEffect(() => {
    loadRequests();
  }, []);

  async function loadRequests() {
    try {
      const apps = await leaveApi.getApplications({ authority_role: "SUBSTITUTE", status: "AWAITING_SUBSTITUTE" });
      setRequests(apps);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleAction(appId: number, action: "ACCEPT" | "DECLINE") {
    try {
      await leaveApi.respondSubstitute({
        substitute_id: substituteId,
        application_id: appId,
        action,
        remarks
      });
      alert(`Substitute request ${action}ED successfully!`);
      setRemarks("");
      loadRequests();
    } catch (err: any) {
      alert(err.message || "Failed to submit response");
    }
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>Substitute Responsibility Inbox</h2>
      <p>Logged in as Substitute: <strong>Prof. Jones ({substituteId})</strong></p>

      {requests.length === 0 ? (
        <div style={{ padding: "1.5rem", backgroundColor: "#f9f9f9", borderRadius: "4px", border: "1px solid #ccc" }}>
          No pending substitute requests assigned to you.
        </div>
      ) : (
        requests.map((app) => (
          <div key={app.id} style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "8px", marginBottom: "1rem", backgroundColor: "#fff" }}>
            <h4>Leave Application #{app.id} — {app.applicant_name} ({app.department})</h4>
            <p><strong>Category:</strong> {app.category} | <strong>Period:</strong> {app.start_date} to {app.end_date} ({app.requested_days} days)</p>
            <p><strong>Purpose:</strong> {app.purpose}</p>

            <div style={{ marginTop: "1rem" }}>
              <input
                type="text"
                placeholder="Remarks / comments (optional)"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                style={{ width: "60%", padding: "0.5rem", marginRight: "1rem" }}
              />
              <button onClick={() => handleAction(app.id, "ACCEPT")} style={{ padding: "0.5rem 1rem", backgroundColor: "#28a745", color: "#fff", border: "none", borderRadius: "4px", marginRight: "0.5rem", cursor: "pointer" }}>
                Accept Responsibility
              </button>
              <button onClick={() => handleAction(app.id, "DECLINE")} style={{ padding: "0.5rem 1rem", backgroundColor: "#dc3545", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                Decline
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
