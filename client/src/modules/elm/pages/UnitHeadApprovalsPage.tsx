import { useEffect, useState } from "react";
import { fetchUnitHeadQueue, reviewUnitHead, type LeaveApplication } from "../api";

export default function UnitHeadApprovalsPage() {
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
      const data = await fetchUnitHeadQueue();
      setQueue(data);
    } catch (err: any) {
      setMessage(err.message || "Failed to load unit head queue.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(id: number, action: "recommend" | "approve" | "reject") {
    const remarks = remarksMap[id] || (action === "reject" ? "Rejected by Unit Head" : "Approved / Recommended by Unit Head");
    try {
      await reviewUnitHead(id, action, remarks);
      setMessage(`Application #${id} successfully updated with action: ${action.toUpperCase()}.`);
      setQueue((prev) => prev.filter((item) => item.id !== id));
    } catch (err: any) {
      setMessage(err.message || "Failed to submit unit head review.");
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Unit Head (HOD / Section Head) Approvals Queue</h2>
      <p style={{ color: "#666" }}>
        Review departmental leave applications. Per institutional policy: CL and RH receive final sanction here; EL, COL, SCL, and VL are recommended and forwarded to the Sanctioning Authority (Dean/Director).
      </p>

      {message && (
        <div style={{ padding: "0.75rem", backgroundColor: "#f0f9ff", border: "1px solid #bae6fd", marginBottom: "1rem" }}>
          {message}
        </div>
      )}

      {loading ? (
        <p>Loading pending reviews...</p>
      ) : queue.length === 0 ? (
        <p>No applications currently pending your recommendation or approval.</p>
      ) : (
        <table border={1} cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginTop: "1rem" }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th>App ID</th>
              <th>Applicant</th>
              <th>Type</th>
              <th>Dates</th>
              <th>Total Days</th>
              <th>Substitute Status</th>
              <th>Reason & Station</th>
              <th>Review Remarks</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((app) => {
              const isDirectSanction = ["CL", "RH"].includes(app.leave_type);
              return (
                <tr key={app.id}>
                  <td>#{app.id}</td>
                  <td>{app.applicant_id}</td>
                  <td>
                    <strong>{app.leave_type}</strong>
                    {app.is_half_day && " (Half-day)"}
                  </td>
                  <td>{app.start_date} to {app.end_date}</td>
                  <td>{app.total_days}</td>
                  <td>
                    {app.substitute_id ? (
                      <span style={{ color: app.substitute_status === "ACCEPTED" ? "#16a34a" : "#ca8a04" }}>
                        {app.substitute_id} ({app.substitute_status})
                      </span>
                    ) : (
                      "N/A"
                    )}
                  </td>
                  <td>
                    <div>{app.reason}</div>
                    {app.requires_station_leave && (
                      <div style={{ fontSize: "0.85rem", color: "#4b5563" }}>
                        Station Leave: {app.station_leave_address}
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
                    {isDirectSanction ? (
                      <button
                        onClick={() => handleReview(app.id, "approve")}
                        style={{ padding: "0.3rem 0.6rem", marginRight: "0.4rem", background: "#16a34a", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                      >
                        Approve (Final)
                      </button>
                    ) : (
                      <button
                        onClick={() => handleReview(app.id, "recommend")}
                        style={{ padding: "0.3rem 0.6rem", marginRight: "0.4rem", background: "#2563eb", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                      >
                        Recommend & Forward
                      </button>
                    )}
                    <button
                      onClick={() => handleReview(app.id, "reject")}
                      style={{ padding: "0.3rem 0.6rem", background: "#dc2626", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                    >
                      Reject
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
