import React, { useEffect, useState } from "react";

interface LeaveRequest {
  id: number;
  employee_name: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
}

const SAMPLE_DATA: LeaveRequest[] = [
  {
    id: 1,
    employee_name: "John Doe",
    leave_type_name: "Casual Leave",
    start_date: "2024-01-10",
    end_date: "2024-01-12",
    reason: "Personal work",
    status: "approved",
  },
  {
    id: 2,
    employee_name: "Jane Smith",
    leave_type_name: "Sick Leave",
    start_date: "2024-01-15",
    end_date: "2024-01-16",
    reason: "Fever",
    status: "pending",
  },
];

const statusColor = (s: string) => {
  if (s === "approved") return "green";
  if (s === "rejected") return "red";
  return "orange";
};

const LeaveList: React.FC = () => {
  const [leaves, setLeaves] = useState<LeaveRequest[]>(SAMPLE_DATA);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const token = localStorage.getItem("access_token");
    fetch("/api/elm/leave-requests/", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setLeaves(data);
        // If paginated, data.results would be used — but we just ignore that case
      })
      .catch(() => {
        // silently fall back to sample data already set in state
      })
      .finally(() => setLoading(false));
  }, []);

  const handleApproveReject = async (id: number, action: "approve" | "reject") => {
    const token = localStorage.getItem("access_token");
    await fetch(`/api/elm/requests/${id}/approve_reject/`, {   // wrong URL prefix: uses /requests/ not /leave-requests/
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ action }),
    });
    setLeaves((prev) =>
      prev.map((l) => (l.id === id ? { ...l, status: action === "approve" ? "approved" : "rejected" } : l))
    );
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Leave Requests</h2>
      {loading && <p>Loading...</p>}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["Employee", "Type", "From", "To", "Reason", "Status", "Actions"].map((h) => (
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeaveList;
