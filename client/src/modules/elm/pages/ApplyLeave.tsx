import { useState, type FormEvent } from "react";
import { http, errorMessage } from "../../../lib/http";

export default function ApplyLeave() {
  const [form, setForm] = useState({ leave_type: "", start_date: "", end_date: "", comments: "" });
  const [msg, setMsg] = useState("");

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg("");
    try {
      await http.post("/elm/leaves/", { ...form, leave_type: Number(form.leave_type) });
      setMsg("Leave applied successfully.");
      setForm({ leave_type: "", start_date: "", end_date: "", comments: "" });
    } catch (err) {
      setMsg("Error: " + errorMessage(err));
    }
  };

  return (
    <form onSubmit={submit} style={{ display: "grid", gap: 12, maxWidth: 400 }}>
      <h1>Apply for Leave</h1>
      <label>Leave type ID
        <input required type="number" value={form.leave_type} onChange={e => set("leave_type", e.target.value)} />
      </label>
      <label>Start date
        <input required type="date" value={form.start_date} onChange={e => set("start_date", e.target.value)} />
      </label>
      <label>End date
        <input required type="date" value={form.end_date} onChange={e => set("end_date", e.target.value)} />
      </label>
      <label>Reason
        <textarea value={form.comments} onChange={e => set("comments", e.target.value)} />
      </label>
      <button type="submit">Apply</button>
      {msg && <p>{msg}</p>}
    </form>
  );
}