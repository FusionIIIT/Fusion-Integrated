import { useEffect, useState } from "react";
import { fetchSanctionQueue, reviewSanction, type LeaveApplication } from "../api";

export default function SanctioningQueuePage() {
  const [queue, setQueue] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [remarksMap, setRemarksMap] = useState<Record<number, string>>({});

  useEffect(() => {
    loadQueue();
  }, []);

  async function loadQueue() {
    setLoading(true);
    try {
      const data = await fetchSanctionQueue();
      setQueue(data);
    } catch (err: any) {
      setMessage(err.message || "Failed to load sanctioning queue.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSanction(id: number, action: "approve" | "reject") {
    const remarks = remarksMap[id] || (action === "approve" ? "Sanctioned by Competent Authority" : "Rejected by Competent Authority");
    try {
      await reviewSanction(id, action, remarks);
      setMessage(`Application #${id} has been ${action === "approve" ? "Approved & Sanctioned" : "Rejected"}.`);
      setQueue((prev) => prev.filter((item) => item.id !== id));
    } catch (err: any) {
      setMessage(err.message || "Failed to execute sanction decision.");
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Sanctioning Authority Queue (Dean / Director)</h2>
      <p style={{ color: "#666" }}>
        Review long-leave applications (EL, COL, SCL, VL) recommended by Unit Heads for institutional sanction.
      </p>

      {message && (
        <div style={{ padding: "0.75rem", backgroundColor: "#f0f9ff", border: "1px solid #bae6fd", marginBottom: "1rem" }}>
          {message}
        </div>
      )}

      {loading ? (
        <p>Loading sanction queue...</p>
      ) : queue.length === 0 ? (
        <p>No applications currently awaiting institutional sanction.</p>
      ) : (
        <table border={1} cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginTop: "1rem" }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th>App ID</th>
              <th>Applicant</th>
              <th>Type</th>
              <th>Dates</th>
              <th>Days</th>
              <th>Unit Head Recommendation</th>
              <th>Reason & Station</th>
              <th>Sanction Remarks</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((app) => (
              <tr key={app.id}>
                <td>#{app.id}</td>
                <td>{app.applicant_id}</td>
                <td>
                  <strong>{app.leave_type}</strong>
                  {app.is_extension && <span style={{ color: "#d97706", display: "block", fontSize: "0.8rem" }}>Extension</span>}
                </td>
                <td>{app.start_date} to {app.end_date}</td>
                <td>{app.total_days}</td>
                <td>
                  <div style={{ color: "#16a34a", fontWeight: "bold" }}>{app.unit_head_recommendation || "RECOMMENDED"}</div>
                  <div style={{ fontSize: "0.85rem", color: "#555" }}>{app.unit_head_remarks || "No remarks"}</div>
                </td>
                <td>
                  <div>{app.reason}</div>
                  {app.requires_station_leave && (
                    <div style={{ fontSize: "0.85rem", color: "#4b5563" }}>
                      Station: {app.station_leave_address}
                    </div>
                  )}
                </td>
                <td>
                  <input
                    type="text"
                    placeholder="Remarks..."
                    value={remarksMap[app.id] || ""}
                    onChange={(e) => setRemarksMap({ ...remarksMap, [app.id]: e.target.value })}
                    style={{ width: "100%", padding: "0.25rem" }}
                  />
                </td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button
                    onClick={() => handleSanction(app.id, "approve")}
                    style={{ padding: "0.3rem 0.6rem", marginRight: "0.4rem", background: "#16a34a", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                  >
                    Sanction (Approve)
                  </button>
                  <button
                    onClick={() => handleSanction(app.id, "reject")}
                    style={{ padding: "0.3rem 0.6rem", background: "#dc2626", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                  >
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
