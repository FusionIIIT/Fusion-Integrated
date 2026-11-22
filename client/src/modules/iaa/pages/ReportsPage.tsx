import { useEffect, useState } from "react";
import { iaaApi } from "../api/client";

export default function ReportsPage() {
  const [data, setData] = useState<Record<string, Array<{ status: string; total: number }>>>({});
  const [error, setError] = useState("");
  useEffect(() => { iaaApi.report().then(setData).catch((e) => setError(e.message)); }, []);
  return <main className="iaa-page"><header><h1>IAA reports</h1><p>Read-only summaries of workflow status.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <p><a href={iaaApi.exportReport()} target="_blank" rel="noreferrer">Export CSV</a></p>
    <div className="iaa-report-grid">{Object.entries(data).map(([name, rows]) => <section className="iaa-card" key={name}><h2>{name.replaceAll("_", " ")}</h2>{rows.map((row) => <p key={row.status}><span className="iaa-status">{row.status}</span> <strong>{row.total}</strong></p>)}</section>)}</div>
  </main>;
}
