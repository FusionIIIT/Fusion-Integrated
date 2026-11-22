import { useEffect, useState, type FormEvent } from "react";
import { iaaApi, type IaaRecord } from "../api/client";

export default function TravelClaimsPage() {
  const [rows, setRows] = useState<IaaRecord[]>([]);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<Array<{ id: number; active_role: string; action: string; from_status: string; to_status: string; occurred_at: string }>>([]);
  const [form, setForm] = useState({ department: "", trip_start: "", trip_end: "", purpose: "", amount: "", document_urls: "" });
  const refresh = () => iaaApi.taClaims().then((p) => setRows(p.results)).catch((e) => setError(e.message));
  useEffect(() => { void refresh(); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      const supporting_documents = await Promise.all(form.document_urls.split(",").map((url) => url.trim()).filter(Boolean).map(async (drive_url) => ({ document_id: (await iaaApi.attachDocument("ta", drive_url)).id })));
      await iaaApi.submitTaClaim({ ...form, amount: form.amount, supporting_documents });
      setForm({ department: "", trip_start: "", trip_end: "", purpose: "", amount: "", document_urls: "" });
      await refresh();
    } catch (e) { setError((e as Error).message); }
  }
  async function financeAction(id: number, decision: "query" | "verify") {
    const text = window.prompt(decision === "query" ? "Clarification question:" : "Finance notes (optional):", "");
    if (text === null) return;
    try { await iaaApi.reviewTa(id, decision, text); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  return <main className="iaa-page"><header><h1>Travel allowance claims</h1><p>Track the status and history of your submitted claims.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <form className="iaa-card iaa-form" onSubmit={submit}><h2>Submit a claim</h2>
      <label>Department<input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} required /></label>
      <label>Trip start<input type="date" value={form.trip_start} onChange={(e) => setForm({ ...form, trip_start: e.target.value })} required /></label>
      <label>Trip end<input type="date" value={form.trip_end} onChange={(e) => setForm({ ...form, trip_end: e.target.value })} required /></label>
      <label>Claimed amount<input type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required /></label>
      <label>Purpose<textarea value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} required /></label>
      <label>Google Drive evidence URL<input value={form.document_urls} onChange={(e) => setForm({ ...form, document_urls: e.target.value })} required /></label>
      <p className="iaa-muted">Share each document from Drive and paste its link. Every link is validated and attached to your account.</p>
      <button>Submit claim</button>
    </form>
    <section className="iaa-card"><div className="iaa-table-wrap"><table><thead><tr><th>Claim</th><th>Purpose</th><th>Department</th><th>Amount</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.id}><td>#{row.id}</td><td>{row.purpose}</td><td>{row.department}</td><td>{row.amount}</td><td><span className="iaa-status">{row.status.replaceAll("_", " ")}</span></td><td>{new Date(row.created_at).toLocaleDateString()}</td><td><button className="iaa-button-secondary" onClick={() => iaaApi.history("ta", row.id).then(setHistory).catch((e) => setError(e.message))}>History</button> {row.status === "query_raised" && <button onClick={() => { const answer = window.prompt("Response to Finance clarification:"); if (answer?.trim()) iaaApi.respond("ta", row.id, answer).then(refresh).catch((e) => setError(e.message)); }}>Respond</button>} {(row.status === "submitted" || row.status === "query_responded") && <><button onClick={() => financeAction(row.id, "verify")}>Verify</button> <button className="iaa-button-secondary" onClick={() => financeAction(row.id, "query")}>Request clarification</button></>} {(row.status === "verified" || row.status === "approved") && <button onClick={() => iaaApi.recordFinancialItem("ta", row.id).then(refresh).catch((e) => setError(e.message))}>Record internally</button>}</td></tr>)}</tbody>
    </table></div>{rows.length === 0 && <p className="iaa-muted">No travel claims found.</p>}</section>
    {history.length > 0 && <section className="iaa-card"><h2>Claim history</h2>{history.map((event) => <p key={event.id}>{event.from_status || "Created"} → {event.to_status || event.action} · {event.active_role} · {new Date(event.occurred_at).toLocaleString()}</p>)}</section>}
  </main>;
}
