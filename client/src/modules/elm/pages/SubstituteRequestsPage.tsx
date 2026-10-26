import { useState } from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { useSubstituteQueue, decideSubstitute } from "../api/hooks";

export function SubstituteRequestsPage() {
  const {requests, loading, error, refetch} = useSubstituteQueue();
  const [notes, setNotes] = useState<Record<string,string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  async function respond(id: string, accept: boolean) {
    setBusy(true); setFailure("");
    try { await decideSubstitute(id, accept, notes[id] || ""); await refetch(); }
    catch (err) {setFailure(errorMessage(err));}
    finally {setBusy(false);}
  }
  return <section><PageHeader title="Substitute requests" subtitle="Accept or decline responsibility coverage" />
    {(error || failure) && <p role="alert">{error || failure}</p>}{loading && <p>Loading…</p>}
    {!loading && !requests.length && <p>No pending nominations.</p>}
    {requests.map(r=><article key={r.id} style={{border:"1px solid #ddd", padding:16, marginBottom:16}}>
      <h3>Employee {r.applicant_user_id}</h3><p>{r.start_date} to {r.end_date}</p>
      <label>Response remarks <textarea value={notes[r.id] || ""} onChange={e=>setNotes({...notes,[r.id]:e.target.value})} /></label>
      <button disabled={busy} onClick={()=>respond(r.id,true)}>Accept</button>{" "}
      <button disabled={busy} onClick={()=>respond(r.id,false)}>Decline</button>
    </article>)}
  </section>;
}
