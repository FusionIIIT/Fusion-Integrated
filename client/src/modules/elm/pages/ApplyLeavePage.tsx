import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { submitLeave } from "../api/hooks";
import type { LeaveType } from "../api/types";

export function ApplyLeavePage() {
  const navigate = useNavigate();
  const [type, setType] = useState<LeaveType>("CL");
  const [half, setHalf] = useState(false);
  const [station, setStation] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const value = (key: string) => String(data.get(key) || "").trim();
    setBusy(true); setError("");
    try {
      await submitLeave({leave_type: type, start_date: value("start"), end_date: value("end"),
        reason: value("reason"), is_half_day: half && type === "CL",
        half_day_session: half && type === "CL" ? value("session") : undefined,
        substitute_id: value("substitute") || undefined, evidence_reference: value("evidence"),
        station_leave: station, station_leave_address: station ? value("address") : undefined,
        out_of_station_from: station ? value("departure") : undefined,
        out_of_station_to: station ? value("return") : undefined});
      navigate("/elm/mine");
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <section style={{maxWidth: 760, margin: "auto"}}>
    <PageHeader title="Apply for leave" subtitle="Your entitlement and leave days are checked against the institute calendars." />
    {error && <p role="alert">{error}</p>}
    <form onSubmit={submit} style={{display:"grid", gap:16}}>
      <label>Leave category <select aria-label="Leave category" value={type} onChange={e => {setType(e.target.value as LeaveType); setHalf(false);}}>
        <option value="CL">Casual leave</option><option value="RH">Restricted holiday</option>
        <option value="SCL">Special casual leave</option><option value="EL">Earned leave</option>
        <option value="COL">Commuted leave</option><option value="VL">Vacation leave</option>
      </select></label>
      <label>Start date <input aria-label="Start date" name="start" type="date" required /></label>
      <label>End date <input aria-label="End date" name="end" type="date" required /></label>
      {type === "CL" && <><label><input type="checkbox" checked={half} onChange={e=>setHalf(e.target.checked)} /> Half-day CL</label>
        {half && <label>Session <select name="session" aria-label="Session"><option value="FN">First half</option><option value="AN">Second half</option></select></label>}</>}
      <label>Reason <textarea name="reason" required maxLength={4000} /></label>
      <label>Substitute employee ID <input name="substitute" inputMode="numeric" pattern="[1-9][0-9]*" /><small> Required when your responsibility coverage policy requires a substitute.</small></label>
      {type === "COL" && <label>Medical evidence reference <input name="evidence" maxLength={2000} /></label>}
      <label><input type="checkbox" checked={station} onChange={e=>setStation(e.target.checked)} /> Leaving Jabalpur during this leave</label>
      {station && <fieldset><legend>Station leave details</legend>
        <label>Contact address <textarea name="address" required /></label>
        <label>Departure <input name="departure" type="date" required /></label>
        <label>Return <input name="return" type="date" required /></label>
      </fieldset>}
      <button type="submit" disabled={busy}>{busy ? "Submitting…" : "Submit application"}</button>
    </form>
  </section>;
}
