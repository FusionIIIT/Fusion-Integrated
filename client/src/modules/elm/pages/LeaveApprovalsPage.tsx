import React, { useState } from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovalsQueue, decideApproval } from "../api/hooks";

export function LeaveApprovalsPage() {
  const { requests, loading, error, refetch } = useApprovalsQueue();
  const [remarks, setRemarks] = useState<{ [id: string]: string }>({});

  const handleDecision = async (id: string, approve: boolean, forward: boolean = false) => {
    const note = remarks[id] || "";
    await decideApproval(id, approve, note, forward);
    refetch();
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <PageHeader title="Leave Approval Queue" subtitle="Review and recommend departmental leave requests" />
      {loading && <p>Loading approval queue...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}
      {!loading && requests.length === 0 && (
        <div style={{ textAlign: "center", padding: "3rem", background: "#f8fafc", borderRadius: 8 }}>
          <p style={{ color: "#64748b" }}>No pending requests requiring your review.</p>
        </div>
      )}
      {!loading && requests.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {requests.map((r) => (
            <div key={r.id} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontWeight: 700, fontSize: 16 }}>{r.applicant_user_id} - {r.leave_type} ({r.duration_days} days)</span>
                <span style={{ color: "#64748b", fontSize: 13 }}>{r.start_date} to {r.end_date}</span>
              </div>
              <p style={{ margin: "4px 0 8px", color: "#334155" }}><strong>Reason:</strong> {r.reason}</p>
              {r.station_leave && (
                <p style={{ margin: "4px 0 8px", color: "#0369a1" }}>
                  <strong>Station Leave Destination:</strong> {r.station_leave_address}
                </p>
              )}
              {r.substitute_user_id && (
                <p style={{ margin: "4px 0 8px", color: "#166534" }}>
                  <strong>Substitute:</strong> {r.substitute_user_id} (Status: {r.substitute_status})
                </p>
              )}
              <div style={{ marginTop: 12, display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Decision remarks..."
                  value={remarks[r.id] || ""}
                  onChange={(e) => setRemarks({ ...remarks, [r.id]: e.target.value })}
                  style={{ flex: 1, padding: 6, borderRadius: 4, border: "1px solid #cbd5e1" }}
                />
                <button
                  onClick={() => handleDecision(r.id, true, false)}
                  style={{ background: "#16a34a", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 4, cursor: "pointer" }}
                >
                  Approve
                </button>
                <button
                  onClick={() => handleDecision(r.id, true, true)}
                  style={{ background: "#2563eb", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 4, cursor: "pointer" }}
                >
                  Forward to Authority
                </button>
                <button
                  onClick={() => handleDecision(r.id, false, false)}
                  style={{ background: "#dc2626", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 4, cursor: "pointer" }}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
