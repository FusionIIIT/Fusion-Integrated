import { useEffect, useState } from "react";
import { http, errorMessage } from "../../../lib/http";

type Leave = { id: number; leave_type: number; start_date: string; end_date: string; status: string; comments: string };

export default function MyLeaves() {
  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const { data } = await http.get("/elm/leaves/mine/");
      setLeaves(data.results ?? data);
    } catch (err) {
      setMsg("Error: " + errorMessage(err));
    }
  };
  useEffect(() => { load(); }, []);

  const cancel = async (id: number) => {
    try {
      await http.post(`/elm/leaves/${id}/cancel/`, {});
      load();
    } catch (err) {
      setMsg("Error: " + errorMessage(err));
    }
  };

  return (
    <div>
      <h1>My Leave Applications</h1>
      {msg && <p>{msg}</p>}
      <table>
        <thead><tr><th>Type</th><th>From</th><th>To</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {leaves.map(l => (
            <tr key={l.id}>
              <td>{l.leave_type}</td><td>{l.start_date}</td><td>{l.end_date}</td><td>{l.status}</td>
              <td>{l.status === "pending" && <button onClick={() => cancel(l.id)}>Cancel</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {leaves.length === 0 && !msg && <p>No leave applications yet.</p>}
    </div>
  );
}