import React, { useState } from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubstituteQueue, decideSubstitute } from "../api/hooks";

export function SubstituteRequestsPage() {
  const { requests, loading, error, refetch } = useSubstituteQueue();
  const [remarks, setRemarks] = useState<{ [id: string]: string }>({});

  const handleDecision = async (id: string, accept: boolean) => {
    const note = remarks[id] || "";
    await decideSubstitute(id, accept, note);
    refetch();
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <PageHeader title="Substitute Nominations" subtitle="Requests where you have been nominated as substitute" />
      {loading && <p>Loading substitute nominations...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}
      {!loading && requests.length === 0 && (
        <div style={{ textAlign: "center", padding: "3rem", background: "#f8fafc", borderRadius: 8 }}>
          <p style={{ color: "#64748b" }}>No substitute requests pending your response.</p>
        </div>
      )}
      {!loading && requests.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {requests.map((r) => (
            <div key={r.id} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontWeight: 700, fontSize: 16 }}>{r.applicant_user_id} - {r.leave_type}</span>
                <span style={{ color: "#64748b", fontSize: 13 }}>{r.start_date} to {r.end_date} ({r.duration_days} days)</span>
              </div>
              <p style={{ margin: "4px 0 8px", color: "#334155" }}><strong>Reason:</strong> {r.reason}</p>
              <div style={{ marginTop: 12, display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Response note..."
                  value={remarks[r.id] || ""}
                  onChange={(e) => setRemarks({ ...remarks, [r.id]: e.target.value })}
                  style={{ flex: 1, padding: 6, borderRadius: 4, border: "1px solid #cbd5e1" }}
                />
                <button
                  onClick={() => handleDecision(r.id, true)}
                  style={{ background: "#16a34a", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 4, cursor: "pointer" }}
                >
                  Accept Responsibility
                </button>
                <button
                  onClick={() => handleDecision(r.id, false)}
                  style={{ background: "#dc2626", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 4, cursor: "pointer" }}
                >
                  Decline
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
