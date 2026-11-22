import { useEffect, useState, type FormEvent } from "react";
import { iaaApi, type IaaRecord } from "../api/client";

export default function ExpenseRequestsPage() {
  const [rows, setRows] = useState<IaaRecord[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<Array<{ id: number; active_role: string; action: string; from_status: string; to_status: string; occurred_at: string }>>([]);
  const [form, setForm] = useState({ request_type: "expense", amount: "", department: "", description: "", document_urls: "" });
  const refresh = () => iaaApi.expenses().then((page) => setRows(page.results)).catch((e) => setError(e.message));
  useEffect(() => { void refresh(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const supporting_documents = await Promise.all(form.document_urls.split(",").map((url) => url.trim()).filter(Boolean).map(async (drive_url) => ({ document_id: (await iaaApi.attachDocument("expense", drive_url)).id })));
      await iaaApi.createExpense({ ...form, amount: form.amount || null, supporting_documents });
      setForm({ request_type: "expense", amount: "", department: "", description: "", document_urls: "" });
      await refresh();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function financeAction(id: number, decision: "query" | "validate") {
    const text = window.prompt(decision === "query" ? "Clarification question:" : "Finance notes (optional):", "");
    if (text === null) return;
    try { await iaaApi.reviewExpense(id, decision, text); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  async function respond(id: number) {
    const text = window.prompt("Response to Finance clarification:");
    if (!text?.trim()) return;
    try { await iaaApi.respond("expense", id, text); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }

  return <main className="iaa-page">
    <header><h1>Expense and voucher requests</h1><p>Draft requests can be incomplete. Add supporting documents before submitting.</p></header>
    <form className="iaa-card iaa-form" onSubmit={create}>
      <h2>New draft</h2>
      <label>Request type<input value={form.request_type} onChange={(e) => setForm({ ...form, request_type: e.target.value })} required /></label>
      <label>Amount<input type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
      <label>Department<input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} /></label>
      <label>Description<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
      <label>Google Drive evidence URLs (comma separated)<input value={form.document_urls} onChange={(e) => setForm({ ...form, document_urls: e.target.value })} /></label>
      <p className="iaa-muted">Share each document from Drive and paste its link. Every link is validated and attached to your account.</p>
      <button disabled={busy}>Save draft</button>
    </form>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <section className="iaa-card"><h2>Requests</h2><div className="iaa-table-wrap"><table>
      <thead><tr><th>Request</th><th>Department</th><th>Amount</th><th>Status</th><th>Created</th><th /></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.id}><td>#{row.id} · {row.request_type}</td><td>{row.department}</td><td>{row.amount ?? "—"}</td><td><span className="iaa-status">{row.status.replaceAll("_", " ")}</span></td><td>{new Date(row.created_at).toLocaleDateString()}</td><td><button className="iaa-button-secondary" onClick={() => iaaApi.history("expense", row.id).then(setHistory).catch((e) => setError(e.message))}>History</button> {row.status === "draft" && <button onClick={() => iaaApi.submitExpense(row.id).then(refresh).catch((e) => setError(e.message))}>Submit</button>} {row.status === "query_raised" && <button onClick={() => respond(row.id)}>Respond</button>} {(row.status === "submitted" || row.status === "query_responded") && <><button onClick={() => financeAction(row.id, "validate")}>Validate</button> <button className="iaa-button-secondary" onClick={() => financeAction(row.id, "query")}>Request clarification</button></>} {row.status === "approved" && <button onClick={() => iaaApi.recordFinancialItem("expense", row.id).then(refresh).catch((e) => setError(e.message))}>Record internally</button>}</td></tr>)}</tbody>
      </table></div>{rows.length === 0 && <p className="iaa-muted">No requests yet.</p>}</section>
    {history.length > 0 && <section className="iaa-card"><h2>Request history</h2>{history.map((event) => <p key={event.id}>{event.from_status || "Created"} → {event.to_status || event.action} · {event.active_role} · {new Date(event.occurred_at).toLocaleString()}</p>)}</section>}
  </main>;
}
