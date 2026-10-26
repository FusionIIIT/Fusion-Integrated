import React, { useEffect, useState } from "react";
import { leaveApi, LeaveApplication } from "../api/leaveApi";

export default function ApprovalQueuePage() {
  const [role, setRole] = useState<string>("UNIT_HEAD");
  const [apps, setApps] = useState<LeaveApplication[]>([]);
  const [remarks, setRemarks] = useState<string>("");

  useEffect(() => {
    loadQueue();
  }, [role]);

  async function loadQueue() {
    try {
      const data = await leaveApi.getApplications({ authority_role: role });
      setApps(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleUnitHeadDecision(appId: number, outcome: string) {
    try {
      await leaveApi.unitHeadReview({
        reviewer_id: "UH001",
        reviewer_name: "HOD CSE",
        application_id: appId,
        outcome,
        remarks
      });
      alert(`Unit Head decision recorded: ${outcome}`);
      setRemarks("");
      loadQueue();
    } catch (err: any) {
      alert(err.message || "Failed to record decision");
    }
  }

  async function handleFinalDecision(appId: number, decision: "APPROVE" | "REJECT") {
    try {
      await leaveApi.finalSanction({
        authority_id: "DEAN01",
        authority_name: "Dean Academics",
        authority_role: role,
        application_id: appId,
        decision,
        remarks
      });
      alert(`Final sanction decision recorded: ${decision}`);
      setRemarks("");
      loadQueue();
    } catch (err: any) {
      alert(err.message || "Failed to record final decision");
    }
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>ELM Approval & Recommendation Queue</h2>

      <div style={{ marginBottom: "1.5rem" }}>
        <label style={{ fontWeight: "bold", marginRight: "1rem" }}>Filter by Role:</label>
        <select value={role} onChange={(e) => setRole(e.target.value)} style={{ padding: "0.5rem" }}>
          <option value="UNIT_HEAD">Unit Head Review Queue</option>
          <option value="DEPUTY_REGISTRAR">Establishment Verification Queue</option>
          <option value="SANCTIONING_AUTHORITY">Sanctioning Authority (Dean/Registrar) Queue</option>
          <option value="DIRECTOR">Director Self-Sanction Queue</option>
        </select>
      </div>

      {apps.length === 0 ? (
        <div style={{ padding: "1.5rem", backgroundColor: "#f9f9f9", borderRadius: "4px", border: "1px solid #ccc" }}>
          No pending applications in the {role} queue.
        </div>
      ) : (
        apps.map((app) => (
          <div key={app.id} style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "8px", marginBottom: "1rem", backgroundColor: "#fff" }}>
            <h4>Leave Application #{app.id} — {app.applicant_name} ({app.department})</h4>
            <p><strong>Category:</strong> {app.category} | <strong>Period:</strong> {app.start_date} to {app.end_date} ({app.requested_days} days)</p>
            <p><strong>Purpose:</strong> {app.purpose}</p>
            {app.unit_head_recommendation !== "NONE" && (
              <p><strong>Unit Head Recommendation:</strong> {app.unit_head_recommendation}</p>
            )}

            <div style={{ marginTop: "1rem" }}>
              <input
                type="text"
                placeholder="Reviewer remarks..."
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                style={{ width: "50%", padding: "0.5rem", marginRight: "1rem" }}
              />

              {role === "UNIT_HEAD" && ["CL", "RH"].includes(app.category) && (
                <>
                  <button onClick={() => handleUnitHeadDecision(app.id, "APPROVE")} style={{ padding: "0.5rem 1rem", backgroundColor: "#28a745", color: "#fff", border: "none", borderRadius: "4px", marginRight: "0.5rem", cursor: "pointer" }}>
                    Approve (Final)
                  </button>
                  <button onClick={() => handleUnitHeadDecision(app.id, "REJECT")} style={{ padding: "0.5rem 1rem", backgroundColor: "#dc3545", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                    Reject (Final)
                  </button>
                </>
              )}

              {role === "UNIT_HEAD" && !["CL", "RH"].includes(app.category) && (
                <>
                  <button onClick={() => handleUnitHeadDecision(app.id, "RECOMMENDED")} style={{ padding: "0.5rem 1rem", backgroundColor: "#0066cc", color: "#fff", border: "none", borderRadius: "4px", marginRight: "0.5rem", cursor: "pointer" }}>
                    Recommend
                  </button>
                  <button onClick={() => handleUnitHeadDecision(app.id, "NOT_RECOMMENDED")} style={{ padding: "0.5rem 1rem", backgroundColor: "#ffc107", color: "#000", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                    Not Recommend
                  </button>
                </>
              )}

              {["SANCTIONING_AUTHORITY", "DIRECTOR"].includes(role) && (
                <>
                  <button onClick={() => handleFinalDecision(app.id, "APPROVE")} style={{ padding: "0.5rem 1rem", backgroundColor: "#28a745", color: "#fff", border: "none", borderRadius: "4px", marginRight: "0.5rem", cursor: "pointer" }}>
                    Approve
                  </button>
                  <button onClick={() => handleFinalDecision(app.id, "REJECT")} style={{ padding: "0.5rem 1rem", backgroundColor: "#dc3545", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                    Reject
                  </button>
                </>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
