import { useState } from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { useApprovalsQueue, decideApproval } from "../api/hooks";

export function LeaveApprovalsPage() {
  const {requests, loading, error, refetch} = useApprovalsQueue();
  const [notes, setNotes] = useState<Record<string,string>>({});
  const [busy, setBusy] = useState("");
  const [failure, setFailure] = useState("");
  async function decide(id: string, approve: boolean) {
    setBusy(id); setFailure("");
    try {await decideApproval(id, approve, notes[id] || ""); await refetch();}
    catch (err) {setFailure(errorMessage(err));}
    finally {setBusy("");}
  }
  return <section><PageHeader title="Leave approvals" subtitle="Requests assigned to your current authority role" />
    {(error || failure) && <p role="alert">{error || failure}</p>}
    {loading && <p>Loading…</p>}{!loading && !requests.length && <p>No assigned requests.</p>}
    {requests.map(r => {
      const recommendation = r.status === "PENDING_UNIT_HEAD" && !["CL", "RH"].includes(r.leave_type);
      return <article key={r.id} style={{border:"1px solid #ddd", padding:16, marginBottom:16}}>
        <h3>{r.applicant_user_id} · {r.leave_type} · {r.request_kind}</h3>
        <p>{r.start_date} to {r.end_date} · {r.duration_days} days</p><p>{r.reason}</p>
        {r.recommendation && <p>Previous review: {r.recommendation}</p>}
        {r.station_leave && <p>Station address: {r.station_leave_address}</p>}
        <label>Decision remarks <textarea value={notes[r.id] || ""} onChange={e=>setNotes({...notes,[r.id]:e.target.value})} /></label>
        <button disabled={!!busy} onClick={()=>decide(r.id,true)}>{recommendation ? "Recommend" : "Approve"}</button>{" "}
        <button disabled={!!busy} onClick={()=>decide(r.id,false)}>{recommendation ? "Do not recommend" : "Reject"}</button>
        {recommendation && <p>Both recommendation outcomes continue to the configured sanctioning authority.</p>}
      </article>;
    })}
  </section>;
}
