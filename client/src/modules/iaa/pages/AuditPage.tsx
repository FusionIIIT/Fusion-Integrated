import { useEffect, useState, type FormEvent } from "react";
import { iaaApi, type IaaRecord } from "../api/client";

export default function AuditPage() {
  const [rows, setRows] = useState<IaaRecord[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ record_type: "expense", record_id: "", finding: "" });
  const [responses, setResponses] = useState<Record<number, string>>({});
  const refresh = () => iaaApi.observations().then((p) => setRows(p.results)).catch((e) => setError(e.message));
  useEffect(() => { void refresh(); }, []);
  async function raise(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await iaaApi.createObservation({ ...form, record_id: Number(form.record_id) }); setForm({ ...form, record_id: "", finding: "" }); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  async function respond(id: number) {
    try { await iaaApi.respondObservation(id, responses[id] ?? ""); setResponses({ ...responses, [id]: "" }); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  async function review(id: number, responseId: number, satisfactory: boolean) {
    const remarks = window.prompt(satisfactory ? "Closure remarks:" : "Why is a revised response needed?", "");
    if (remarks === null) return;
    try { await iaaApi.reviewObservation(id, responseId, satisfactory, remarks); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  return <main className="iaa-page"><header><h1>Audit observations</h1><p>Raise findings, submit corrective actions, and verify responses. Each response remains in the history.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <form className="iaa-card iaa-form" onSubmit={raise}><h2>Raise an observation</h2>
      <label>Record type<select value={form.record_type} onChange={(e) => setForm({ ...form, record_type: e.target.value })}><option value="expense">Expense/voucher</option><option value="ta">Travel claim</option></select></label>
      <label>Record ID<input type="number" min="1" value={form.record_id} onChange={(e) => setForm({ ...form, record_id: e.target.value })} required /></label>
      <label>Finding<textarea value={form.finding} onChange={(e) => setForm({ ...form, finding: e.target.value })} required /></label>
      <button>Raise observation</button>
    </form>
    <section className="iaa-card"><h2>Observation follow-ups</h2>
      {rows.map((row) => <article className="iaa-observation" key={row.id}>
        <header><strong>#{row.id} · {row.record_type} #{row.record_id}</strong><span className="iaa-status">{row.status}</span></header>
        <p>{row.finding}</p>
        {row.responses?.map((response) => <div className="iaa-response" key={response.id}>
          <p>{response.corrective_action}</p>
          {response.satisfactory === null && <><button onClick={() => review(row.id, response.id, true)}>Close as satisfactory</button> <button className="iaa-button-secondary" onClick={() => review(row.id, response.id, false)}>Return for revision</button></>}
        </div>)}
        {row.status === "open" && <div className="iaa-response"><label>Corrective action<textarea value={responses[row.id] ?? ""} onChange={(e) => setResponses({ ...responses, [row.id]: e.target.value })} /></label><button onClick={() => respond(row.id)}>Submit response</button></div>}
      </article>)}
      {rows.length === 0 && <p className="iaa-muted">No audit observations found.</p>}
    </section>
  </main>;
}
