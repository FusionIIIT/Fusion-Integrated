import React from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api/hooks";

export function LeaveBalancePage() {
  const { balances, loading, error } = useLeaveBalances();

  return (
    <div style={{ padding: "1.5rem" }}>
      <PageHeader title="Leave Balance Ledger" subtitle="Annual quotas, availed leaves and pending applications" />
      {loading && <p>Loading balances...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}
      {!loading && balances.length === 0 && (
        <div style={{ textAlign: "center", padding: "3rem", background: "#f8fafc", borderRadius: 8 }}>
          <p style={{ color: "#64748b" }}>No balance records found for current calendar cycle.</p>
        </div>
      )}
      {!loading && balances.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
          {balances.map((b) => (
            <div key={b.id} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: "1.25rem" }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#1e293b", marginBottom: 4 }}>{b.leave_type}</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: "#2563eb", marginBottom: 8 }}>{b.balance} <span style={{ fontSize: 14, fontWeight: 500, color: "#64748b" }}>days left</span></div>
              <div style={{ fontSize: 13, color: "#475569", borderTop: "1px solid #f1f5f9", paddingTop: 8 }}>
                <div>Credited: {b.credited}</div>
                <div>Availed: {b.availed}</div>
                <div>Pending: {b.pending}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
