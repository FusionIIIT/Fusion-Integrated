import React from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useMyLeaves, withdrawLeaveRequest } from "../api/hooks";

export function MyLeavesPage() {
  const { leaves, loading, error, refetch } = useMyLeaves();

  const handleWithdraw = async (id: string) => {
    if (window.confirm("Are you sure you want to withdraw this leave request?")) {
      await withdrawLeaveRequest(id, "Withdrawn by employee");
      refetch();
    }
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <PageHeader title="My Leave Applications" subtitle="Track status of your submitted leave requests" />
        <Link
          to="/elm/apply"
          style={{
            backgroundColor: "#2563eb",
            color: "#fff",
            padding: "0.5rem 1rem",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          + New Leave
        </Link>
      </div>

      {loading && <p>Loading leave records...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}

      {!loading && leaves.length === 0 && (
        <div style={{ textAlign: "center", padding: "3rem", background: "#f8fafc", borderRadius: 8 }}>
          <p style={{ color: "#64748b" }}>No leave requests found. Click "New Leave" to submit an application.</p>
        </div>
      )}

      {!loading && leaves.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8, overflow: "hidden", border: "1px solid #e2e8f0" }}>
          <thead>
            <tr style={{ background: "#f1f5f9", textAlign: "left", fontSize: 13, color: "#475569" }}>
              <th style={{ padding: 12 }}>Category</th>
              <th style={{ padding: 12 }}>Dates</th>
              <th style={{ padding: 12 }}>Days</th>
              <th style={{ padding: 12 }}>Station Leave</th>
              <th style={{ padding: 12 }}>Substitute</th>
              <th style={{ padding: 12 }}>Status</th>
              <th style={{ padding: 12 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {leaves.map((l) => (
              <tr key={l.id} style={{ borderTop: "1px solid #e2e8f0", fontSize: 14 }}>
                <td style={{ padding: 12, fontWeight: 600 }}>{l.leave_type}</td>
                <td style={{ padding: 12 }}>{l.start_date} to {l.end_date}</td>
                <td style={{ padding: 12 }}>{l.duration_days}</td>
                <td style={{ padding: 12 }}>{l.station_leave ? "Yes" : "No"}</td>
                <td style={{ padding: 12 }}>
                  {l.substitute_user_id ? `${l.substitute_user_id} (${l.substitute_status})` : "None"}
                </td>
                <td style={{ padding: 12 }}>
                  <StatusBadge status={l.status} />
                </td>
                <td style={{ padding: 12 }}>
                  {["PENDING_SUBSTITUTE", "PENDING_UNIT_HEAD", "PENDING_AUTHORITY"].includes(l.status) && (
                    <button
                      onClick={() => handleWithdraw(l.id)}
                      style={{ color: "#ef4444", background: "transparent", border: "1px solid #fca5a5", borderRadius: 4, padding: "4px 8px", cursor: "pointer" }}
                    >
                      Withdraw
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
