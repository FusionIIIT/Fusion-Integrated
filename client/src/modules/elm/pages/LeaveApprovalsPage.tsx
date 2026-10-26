import { useEffect, useState } from "react";
import type { LeaveApplication } from "../api";

export default function LeaveApprovalsPage() {
  const [items, setItems] = useState<LeaveApplication[]>([]);

  useEffect(() => {
    fetch("/api/v1/elm/approvals", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setItems(data))
      .catch(() => setItems([]));
  }, []);

  async function handleAction(id: number, action: string) {
    await fetch(`/api/v1/elm/approvals/${id}/review`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, remarks: `Reviewed (${action})` }),
    });
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, status: action.toUpperCase() } : it)));
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Leave Approvals Queue</h2>
      <table border={1} cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Applicant</th>
            <th>Type</th>
            <th>Dates</th>
            <th>Days</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.applicant_id}</td>
              <td>{item.leave_type}</td>
              <td>
                {item.start_date} to {item.end_date}
              </td>
              <td>{item.total_days}</td>
              <td>{item.status}</td>
              <td>
                <button onClick={() => handleAction(item.id, "recommend")} style={{ marginRight: "0.4rem" }}>
                  Recommend
                </button>
                <button onClick={() => handleAction(item.id, "approve")} style={{ marginRight: "0.4rem" }}>
                  Approve
                </button>
                <button onClick={() => handleAction(item.id, "reject")}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
