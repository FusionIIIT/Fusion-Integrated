import { useEffect, useState } from "react";
import { fetchSubstituteRequests, respondSubstitute, type LeaveApplication } from "../api";

export default function SubstituteRequestsPage() {
  const [requests, setRequests] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [remarksMap, setRemarksMap] = useState<Record<number, string>>({});

  useEffect(() => {
    loadRequests();
  }, []);

  async function loadRequests() {
    setLoading(true);
    try {
      const data = await fetchSubstituteRequests();
      setRequests(data);
    } catch (err: any) {
      setMessage(err.message || "Failed to load substitute requests.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResponse(id: number, accept: boolean) {
    const remarks = remarksMap[id] || (accept ? "Consented to substitute" : "Unable to substitute");
    try {
      await respondSubstitute(id, accept, remarks);
      setMessage(`Successfully ${accept ? "accepted" : "declined"} substitute duty for application #${id}.`);
      setRequests((prev) => prev.filter((r) => r.id !== id));
    } catch (err: any) {
      setMessage(err.message || "Failed to submit substitute response.");
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Substitute Responsibility Requests</h2>
      <p style={{ color: "#666" }}>
        Review and provide consent to take over academic and administrative responsibilities for colleagues on leave.
      </p>

      {message && (
        <div style={{ padding: "0.75rem", backgroundColor: "#f0f9ff", border: "1px solid #bae6fd", marginBottom: "1rem" }}>
          {message}
        </div>
      )}

      {loading ? (
        <p>Loading substitute requests...</p>
      ) : requests.length === 0 ? (
        <p>No pending substitute requests.</p>
      ) : (
        <table border={1} cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginTop: "1rem" }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th>App ID</th>
              <th>Applicant</th>
              <th>Leave Type</th>
              <th>Dates</th>
              <th>Total Days</th>
              <th>Reason</th>
              <th>Station Leave</th>
              <th>Remarks</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((req) => (
              <tr key={req.id}>
                <td>#{req.id}</td>
                <td>{req.applicant_id}</td>
                <td>{req.leave_type}</td>
                <td>{req.start_date} to {req.end_date}</td>
                <td>{req.total_days}</td>
                <td>{req.reason}</td>
                <td>{req.requires_station_leave ? `Yes (${req.station_leave_address || "Outstation"})` : "No"}</td>
                <td>
                  <input
                    type="text"
                    placeholder="Remarks..."
                    value={remarksMap[req.id] || ""}
                    onChange={(e) => setRemarksMap({ ...remarksMap, [req.id]: e.target.value })}
                    style={{ width: "100%", padding: "0.25rem" }}
                  />
                </td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button
                    onClick={() => handleResponse(req.id, true)}
                    style={{ padding: "0.3rem 0.6rem", marginRight: "0.5rem", background: "#16a34a", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => handleResponse(req.id, false)}
                    style={{ padding: "0.3rem 0.6rem", background: "#dc2626", color: "white", border: "none", cursor: "pointer", borderRadius: "3px" }}
                  >
                    Decline
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
