import React, { useEffect, useState } from "react";
import { fetchLeaveBalances, LeaveBalance as LeaveBalanceType } from "./api";

export default function LeaveBalancePage() {
  const [balances, setBalances] = useState<LeaveBalanceType[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLeaveBalances()
      .then((data) => {
        setBalances(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading leave balances...</div>;
  if (error) return <div style={{ color: "red" }}>Error: {error}</div>;

  return (
    <div style={{ padding: "24px" }}>
      <h2>Employee Leave Balances</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "16px" }}>
        <thead>
          <tr style={{ background: "#f1f3f5", textAlign: "left" }}>
            <th style={{ padding: "8px", border: "1px solid #dee2e6" }}>Category</th>
            <th style={{ padding: "8px", border: "1px solid #dee2e6" }}>Credited</th>
            <th style={{ padding: "8px", border: "1px solid #dee2e6" }}>Availed</th>
            <th style={{ padding: "8px", border: "1px solid #dee2e6" }}>Remaining Balance</th>
          </tr>
        </thead>
        <tbody>
          {balances.map((b) => (
            <tr key={b.id}>
              <td style={{ padding: "8px", border: "1px solid #dee2e6" }}>
                <strong>{b.leave_type_code}</strong> - {b.leave_type_name}
              </td>
              <td style={{ padding: "8px", border: "1px solid #dee2e6" }}>{b.credited}</td>
              <td style={{ padding: "8px", border: "1px solid #dee2e6" }}>{b.availed}</td>
              <td style={{ padding: "8px", border: "1px solid #dee2e6", color: "green", fontWeight: "bold" }}>
                {b.remaining}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
