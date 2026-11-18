/** Leave request list (employee view) and approvals (approver view).
 *
 *  Fix history:
 *  - C1.1: replaced fetch()+localStorage with shared axios http instance.
 *  - C1.2: URLs corrected to /elm/requests/ and /elm/requests/{id}/approve_reject/.
 *  - C1.4: reads data.results from cursor-paginated response.
 *  - C1.5: real loading and error states — SAMPLE_DATA removed entirely.
 *  - C1.6: Approve/Reject buttons only shown with elm.leave_request.review.
 */
import React, { useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { http, errorMessage } from "../../lib/http";
import type { LeaveRequest, Page, ReviewLeavePayload } from "./api/types";

const statusColor = (s: string) => {
  if (s === "approved") return "green";
  if (s === "rejected") return "red";
  return "orange";
};

const LeaveList: React.FC = () => {
  const { can } = useAuth();
  const canReview = can("elm.leave_request.review");

  const [leaves, setLeaves]   = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setFetchError(null);
    http
      .get<Page<LeaveRequest>>("/elm/requests/")
      .then((r) => setLeaves(r.data.results ?? []))
      .catch((e) => setFetchError(errorMessage(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleApproveReject = async (id: number, action: ReviewLeavePayload["action"]) => {
    setActionError(null);
    try {
      await http.post<LeaveRequest>(`/elm/requests/${id}/approve_reject/`, { action });
      setLeaves((prev) =>
        prev.map((l) =>
          l.id === id ? { ...l, status: action === "approve" ? "approved" : "rejected" } : l,
        ),
      );
    } catch (e) {
      setActionError(errorMessage(e));
    }
  };

  if (loading) return <div style={{ padding: "2rem" }}><p>Loading…</p></div>;
  if (fetchError) return <div style={{ padding: "2rem" }}><p style={{ color: "red" }}>Error: {fetchError}</p></div>;

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Leave Requests</h2>
      {actionError && <p style={{ color: "red" }}>{actionError}</p>}
      {leaves.length === 0 ? (
        <p>No leave requests found.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Employee", "Type", "From", "To", "Reason", "Status",
                ...(canReview ? ["Actions"] : []),
              ].map((h) => (
                <th key={h} style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: "8px" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {leaves.map((l) => (
              <tr key={l.id}>
                <td style={{ padding: "8px" }}>{l.employee_name}</td>
                <td style={{ padding: "8px" }}>{l.leave_type_name}</td>
                <td style={{ padding: "8px" }}>{l.start_date}</td>
                <td style={{ padding: "8px" }}>{l.end_date}</td>
                <td style={{ padding: "8px" }}>{l.reason}</td>
                <td style={{ padding: "8px", color: statusColor(l.status) }}>{l.status}</td>
                {canReview && (
                  <td style={{ padding: "8px" }}>
                    {l.status === "pending" && (
                      <>
                        <button onClick={() => handleApproveReject(l.id, "approve")} style={{ marginRight: 4 }}>
                          Approve
                        </button>
                        <button onClick={() => handleApproveReject(l.id, "reject")}>Reject</button>
                      </>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default LeaveList;
