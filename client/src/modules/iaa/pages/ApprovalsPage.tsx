import { useEffect, useState } from "react";
import { iaaApi, type ApprovalStep } from "../api/client";

export default function ApprovalsPage() {
  const [rows, setRows] = useState<ApprovalStep[]>([]);
  const [details, setDetails] = useState<Record<string, { description?: string; purpose?: string; amount?: string; department?: string }>>({});
  const [error, setError] = useState("");
  const refresh = () => iaaApi.approvals().then(async (p) => {
    setRows(p.results);
    const entries = await Promise.all(p.results.map(async (row) => {
      try {
        const record = row.record_type === "expense" ? await iaaApi.expense(row.record_id) : await iaaApi.taClaim(row.record_id);
        return [`${row.record_type}-${row.record_id}`, record] as const;
      } catch { return [`${row.record_type}-${row.record_id}`, {}] as const; }
    }));
    setDetails(Object.fromEntries(entries));
  }).catch((e) => setError(e.message));
  useEffect(() => { void refresh(); }, []);
  async function decide(row: ApprovalStep, decision: "approve" | "reject") {
    const remarks = window.prompt(`Remarks for ${decision}:`);
    if (!remarks?.trim()) return;
    try { await iaaApi.decide(row.id, decision, remarks); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  return <main className="iaa-page"><header><h1>Approval queue</h1><p>Review assigned requests using the active HoD, Dean, or Director role.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <section className="iaa-card"><div className="iaa-table-wrap"><table><thead><tr><th>Record</th><th>Authority level</th><th>Due</th><th>Decision</th></tr></thead>
      <tbody>{rows.map((row) => { const detail = details[`${row.record_type}-${row.record_id}`]; return <tr key={row.id}><td>{row.record_type === "expense" ? "Expense" : "TA claim"} #{row.record_id}<br /><span className="iaa-muted">{detail?.description ?? detail?.purpose}</span></td><td>{detail?.department}<br />{detail?.amount}</td><td>{row.authority_role.toUpperCase()}</td><td>{row.due_at ? new Date(row.due_at).toLocaleString() : "No deadline configured"}</td><td><button onClick={() => decide(row, "approve")}>Approve</button> <button className="iaa-button-secondary" onClick={() => decide(row, "reject")}>Reject</button></td></tr>; })}</tbody>
    </table></div>{rows.length === 0 && <p className="iaa-muted">No approvals are assigned to your active role.</p>}</section>
  </main>;
}
