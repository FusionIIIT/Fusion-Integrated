import { useEffect, useState } from "react";

import { errorMessage } from "../../../lib/http";
import { getEmployeeBalance } from "../api/api";
import type { EmployeeLeaveBalance } from "../api/types";

export const LeaveBalancePage = () => {
  const [balances, setBalances] = useState<EmployeeLeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getEmployeeBalance()
      .then(setBalances)
      .catch((cause: unknown) => setError(errorMessage(cause)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="leave-balance-page">
      <h2>My Leave Balance</h2>
      {error && <p role="alert">{error}</p>}
      {loading ? <p>Loading balances…</p> : (
        <table>
          <thead><tr>
            <th>Leave type</th><th>Entitlement</th><th>Used</th>
            <th>Remaining</th><th>Carry forward</th>
          </tr></thead>
          <tbody>
            {balances.map((balance) => (
              <tr key={balance.leave_category_code}>
                <td>{balance.leave_category_code}: {balance.leave_category_label}</td>
                <td>{balance.entitlement_days}</td>
                <td>{balance.used_days}</td>
                <td>{balance.remaining_days}</td>
                <td>{balance.carry_forward ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
};
