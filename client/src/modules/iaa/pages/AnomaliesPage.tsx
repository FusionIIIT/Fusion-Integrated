import { useEffect, useState, type FormEvent } from "react";
import { iaaApi } from "../api/client";

type AnomalyRow = { id: number; record_type: string; record_id: number; category: string; description: string; status: string };

export default function AnomaliesPage() {
  const [rows, setRows] = useState<AnomalyRow[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ record_type: "expense", record_id: "", category: "policy_violation", description: "", resolver_role: "finance_staff", resolver_user_id: "" });
  const refresh = () => iaaApi.anomalies().then((p) => setRows(p.results)).catch((e) => setError(e.message));
  useEffect(() => { void refresh(); }, []);
  async function flag(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await iaaApi.flagAnomaly({ ...form, record_id: Number(form.record_id), resolver_user_id: form.resolver_user_id ? Number(form.resolver_user_id) : null }); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  async function resolve(id: number, action: "resolve" | "escalate") {
    const remarks = window.prompt(action === "resolve" ? "Resolution remarks:" : "Escalation reason:");
    if (!remarks?.trim()) return;
    let next: number | undefined; let nextRole: string | undefined;
    if (action === "escalate") {
      const raw = window.prompt("Next designated resolver user ID:"); if (!raw) return; next = Number(raw);
      nextRole = window.prompt("Next resolver role (finance_staff, auditor, hod, dean, director):", "finance_staff") ?? undefined;
      if (!nextRole) return;
    }
    try { await iaaApi.resolveAnomaly(id, action, remarks, next, nextRole); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  return <main className="iaa-page"><header><h1>Material anomalies</h1><p>Review budget and policy exceptions assigned to your active IAA role.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <form className="iaa-card iaa-form" onSubmit={flag}><h2>Flag an anomaly</h2>
      <label>Record type<select value={form.record_type} onChange={(e) => setForm({ ...form, record_type: e.target.value })}><option value="expense">Expense/voucher</option><option value="ta">Travel claim</option></select></label>
      <label>Record ID<input type="number" min="1" value={form.record_id} onChange={(e) => setForm({ ...form, record_id: e.target.value })} required /></label>
      <label>Category<input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required /></label>
      <label>Description<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required /></label>
      <label>Resolver role<select value={form.resolver_role} onChange={(e) => setForm({ ...form, resolver_role: e.target.value })}><option value="finance_staff">Finance Staff</option><option value="auditor">Auditor</option><option value="hod">HoD</option><option value="dean">Dean</option><option value="director">Director</option></select></label>
      <label>Resolver user ID<input type="number" min="1" value={form.resolver_user_id} onChange={(e) => setForm({ ...form, resolver_user_id: e.target.value })} /></label>
      <button>Flag anomaly</button>
    </form>
    <section className="iaa-card"><h2>Anomaly queue</h2>{rows.map((row) => <article className="iaa-observation" key={row.id}>
      <header><strong>{row.category} · {row.record_type} #{row.record_id}</strong><span className="iaa-status">{row.status}</span></header><p>{row.description}</p>
      {row.status !== "resolved" && <><button onClick={() => resolve(row.id, "resolve")}>Resolve</button> <button className="iaa-button-secondary" onClick={() => resolve(row.id, "escalate")}>Escalate</button></>}
    </article>)}{rows.length === 0 && <p className="iaa-muted">No anomalies in this queue.</p>}</section>
  </main>;
}
