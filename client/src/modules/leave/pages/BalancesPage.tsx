import { useQuery } from "@tanstack/react-query";

import { errorMessage, http } from "../../../lib/http";

type Balance = { employee_id: string; leave_type: string; balance: string; last_updated: string };
type Page<T> = { results: T[] };

export default function BalancesPage() {
  const balances = useQuery({
    queryKey: ["leave-cell", "balances"],
    queryFn: async () => (await http.get<Page<Balance>>("/leave/balances/")).data.results,
  });

  return <main>
    <h1>Leave Balances</h1>
    {balances.isPending && <p>Loading balances…</p>}
    {balances.isError && <p role="alert">{errorMessage(balances.error)}</p>}
    {balances.data && (balances.data.length ? <table>
      <thead><tr><th>Leave type</th><th>Available</th><th>Updated</th></tr></thead>
      <tbody>{balances.data.map((row) => <tr key={row.leave_type}>
        <td>{row.leave_type}</td><td>{row.balance}</td>
        <td>{new Date(row.last_updated).toLocaleDateString()}</td>
      </tr>)}</tbody>
    </table> : <p>No leave balances are available yet.</p>)}
  </main>;
}
