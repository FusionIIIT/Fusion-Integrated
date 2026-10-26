import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { http, errorMessage } from "../../../lib/http";
import { useMyLeaves, withdrawLeaveRequest, replaceSubstitute, followupLeave, exportLeave } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

function LeaveActions({leave, done}: {leave: LeaveRequest; done: ()=>unknown}) {
  const [action, setAction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = ["PENDING_SUBSTITUTE","APPLICANT_ACTION","PENDING_UNIT_HEAD","PENDING_AUTHORITY"].includes(leave.status);
  const today = new Date().toLocaleDateString("en-CA");
  const original = leave.request_kind === "LEAVE" && leave.status === "APPROVED" && !leave.actual_end_date;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const reason = String(data.get("reason") || "");
      if (action === "withdraw") await withdrawLeaveRequest(leave.id, reason);
      else if (action === "replace") await replaceSubstitute(leave.id, String(data.get("substitute")));
      else await followupLeave(leave.id, action, {reason, end_date: String(data.get("end") || "") || undefined,
        substitute_id: String(data.get("substitute") || "") || undefined});
      setAction(""); await done();
    } catch (err) {setError(errorMessage(err));}
    finally {setBusy(false);}
  }
  async function download() {
    setError("");
    try {await exportLeave(leave.id);} catch (err) {setError(errorMessage(err));}
  }
  return <div>
    <button onClick={download}>Download / print</button>{" "}
    {pending && <button onClick={()=>setAction("withdraw")}>Withdraw</button>}{" "}
    {leave.status === "APPLICANT_ACTION" && <button onClick={()=>setAction("replace")}>Replace substitute</button>}{" "}
    {original && today < leave.start_date && <button onClick={()=>setAction("cancel")}>Request cancellation</button>}{" "}
    {original && ["EL","COL","VL"].includes(leave.leave_type) && today >= leave.start_date && <>
      <button onClick={()=>setAction("extend")}>Request extension</button>{" "}<button onClick={()=>setAction("resume")}>Submit resumption</button>
    </>}
    {error && <p role="alert">{error}</p>}
    {action && <form onSubmit={submit} style={{marginTop:12,display:"grid",gap:8}}>
      <strong>{action === "replace" ? "Nominate replacement" : action}</strong>
      {action !== "replace" && <label>Reason / details <textarea name="reason" required /></label>}
      {["replace","extend"].includes(action) && <label>Substitute employee ID <input name="substitute" inputMode="numeric" pattern="[1-9][0-9]*" required={action === "replace"} /></label>}
      {["extend","resume"].includes(action) && <label>{action === "resume" ? "Actual resumption date" : "Requested new end date"} <input type="date" name="end" required /></label>}
      <div><button disabled={busy} type="submit">{busy ? "Saving…" : "Confirm"}</button>{" "}<button type="button" disabled={busy} onClick={()=>setAction("")}>Close</button></div>
    </form>}
  </div>;
}

export function MyLeavesPage() {
  const {leaves, loading, error, refetch} = useMyLeaves();
  const [notifications, setNotifications] = useState<{id:string;message:string}[]>([]);
  const [noticeError, setNoticeError] = useState("");
  useEffect(()=> { http.get("/elm/notifications/").then(r=>setNotifications(r.data)).catch(e=>setNoticeError(errorMessage(e))); }, [leaves]);
  return <section><PageHeader title="My leave applications" subtitle="Status, decisions and follow-up requests" action={<Link to="/elm/apply">New application</Link>} />
    {error && <p role="alert">{error}</p>}{loading && <p>Loading…</p>}
    {!loading && !leaves.length && <p>No applications yet.</p>}
    {leaves.map(l=><article key={l.id} style={{border:"1px solid #ddd",padding:16,marginBottom:16}}>
      <h3>{l.leave_type} · {l.request_kind} · {l.status.replaceAll("_"," ")}</h3>
      <p>{l.start_date} to {l.end_date} · {l.duration_days} days</p><p>{l.reason}</p>
      {l.original_id && <p>Original application: {l.original_id}</p>}
      {l.actual_end_date && <p>Reviewed actual end: {l.actual_end_date} · {l.actual_duration_days} days</p>}
      {l.substitute_user_id && <p>Substitute: {l.substitute_user_id} · {l.substitute_status}</p>}
      {l.rejection_reason && <p>Decision reason: {l.rejection_reason}</p>}
      <LeaveActions leave={l} done={refetch} />
      <details><summary>Request history</summary><ol>{l.action_logs?.map(a=><li key={a.id}>{new Date(a.created_at).toLocaleString()}: {a.action} · {a.remarks}</li>)}</ol></details>
    </article>)}
    <details><summary>Notifications</summary>{noticeError && <p role="alert">{noticeError}</p>}<ul>{notifications.map(n=><li key={n.id}>{n.message}</li>)}</ul></details>
  </section>;
}
