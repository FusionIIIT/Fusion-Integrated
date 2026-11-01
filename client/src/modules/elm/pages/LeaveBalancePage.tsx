import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { getEmployeeBalance } from "../api/selectors";

export const LeaveBalancePage = () => {
  const { userId } = useParams();
  const [balances, setBalances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userId) {
      const balanceData = getEmployeeBalance(userId);
      setBalances(Object.values(balanceData));
    }
    setLoading(false);
  }, [userId]);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="leave-balance-page">
      <h2>Leave Balance</h2>
      <table>
        <thead>
          <tr>
            <th>Leave Type</th>
            <th>Remaining</th>
            <th>Used</th>
          </tr>
        </thead>
        <tbody>
          {balances.map((b) => (
            <tr key={b.leave_category.code}>
              <td>{b.leave_category.code}: {b.leave_category.label}</td>
              <td>{b.remaining_days}</td>
              <td>{b.used_days}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};