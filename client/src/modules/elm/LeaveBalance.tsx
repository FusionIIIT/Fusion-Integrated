import { useEffect, useState } from "react";
import { fetchLeaveBalances, type LeaveBalanceRow } from "./api";

const LeaveBalance = () => {
  const [leaveBalances, setLeaveBalances] = useState<LeaveBalanceRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBalances = async () => {
      try {
        const balances = await fetchLeaveBalances();
        setLeaveBalances(balances);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to fetch leave balances.");
      } finally {
        setLoading(false);
      }
    };

    fetchBalances();
  }, []);

  if (loading) return <p>Loading leave balances...</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;

  return (
    <div style={{ padding: "1.5rem" }}>
      <h1>Leave Balances</h1>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ccc" }}>
            <th style={{ padding: "0.5rem" }}>Leave Type ID</th>
            <th style={{ padding: "0.5rem" }}>Balance (Days)</th>
          </tr>
        </thead>
        <tbody>
          {leaveBalances.map((balance) => (
            <tr key={balance.id} style={{ borderBottom: "1px solid #eee" }}>
              <td style={{ padding: "0.5rem" }}>{balance.leave_type}</td>
              <td style={{ padding: "0.5rem" }}>{balance.balance}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeaveBalance;
