import { useEffect, useState } from "react";
import { http, errorMessage } from "../../../lib/http";

type Leave = { id: number; applicant_id: number; leave_type: number; start_date: string; end_date: string; comments: string };

export default function ApproveLeaves() {
  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const { data } = await http.get("/elm/leaves/pending/");
      setLeaves(data.results ?? data);
    } catch (err) {
      setMsg("Error: " + errorMessage(err));
    }
  };
  useEffect(() => { load(); }, []);

  const decide = async (id: number, decision: "approved" | "rejected") => {
    try {
      await http.post(`/elm/leaves/${id}/approve/`, { decision });
      load();
    } catch (err) {
      setMsg("Error: " + errorMessage(err));
    }
  };

  return (
    <div>
      <h1>Pending Leave Applications</h1>
      {msg && <p>{msg}</p>}
      <table>
        <thead><tr><th>Applicant</th><th>Type</th><th>From</th><th>To</th><th>Reason</th><th></th></tr></thead>
        <tbody>
          {leaves.map(l => (
            <tr key={l.id}>
              <td>{l.applicant_id}</td><td>{l.leave_type}</td><td>{l.start_date}</td><td>{l.end_date}</td><td>{l.comments}</td>
              <td>
                <button onClick={() => decide(l.id, "approved")}>Approve</button>{" "}
                <button onClick={() => decide(l.id, "rejected")}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {leaves.length === 0 && !msg && <p>No pending applications.</p>}
    </div>
  );
}