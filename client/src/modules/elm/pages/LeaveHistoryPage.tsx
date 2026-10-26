import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { getApplications } from "../api/api";
import type { LeaveApplication } from "../api/types";

export const LeaveHistoryPage = () => {
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getApplications()
      .then(setApplications)
      .catch((cause: unknown) => setError(errorMessage(cause)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="leave-history-page">
      <h2>Leave History</h2>
      {error && <p role="alert">{error}</p>}
      {loading ? <p>Loading history…</p> : applications.length === 0 ? (
        <p>No leave records found.</p>
      ) : (
        <table>
          <thead><tr>
            <th>Type</th><th>Period</th><th>Status / decision</th><th>Record</th>
          </tr></thead>
          <tbody>
            {applications.map((app) => (
              <tr key={app.id}>
                <td>{app.leave_category_code}</td>
                <td>{app.requested_start} – {app.requested_end}</td>
                <td>{app.status.replaceAll("_", " ")}</td>
                <td><Link to={`/elm/print-application/${app.id}`}>View / print</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
};
