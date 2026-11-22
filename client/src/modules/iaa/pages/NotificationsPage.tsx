import { useEffect, useState } from "react";
import { iaaApi } from "../api/client";

export default function NotificationsPage() {
  const [rows, setRows] = useState<Array<{ id: string; event: string; record_type: string; record_id: number; created_at: string }>>([]);
  const [error, setError] = useState("");
  useEffect(() => { iaaApi.notifications().then((p) => setRows(p.results)).catch((e) => setError(e.message)); }, []);
  return <main className="iaa-page"><header><h1>Notifications and follow-ups</h1><p>Recent IAA updates and actions addressed to your account.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}
    <section className="iaa-card">{rows.map((item) => <article className="iaa-notice" key={item.id}><strong>{item.event.replaceAll("_", " ")}</strong><span>{item.record_type} #{item.record_id}</span><time>{new Date(item.created_at).toLocaleString()}</time></article>)}{rows.length === 0 && <p className="iaa-muted">No notifications.</p>}</section>
  </main>;
}
