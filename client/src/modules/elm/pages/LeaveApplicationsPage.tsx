import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { getApplications, withdrawApplication } from "../api/api";
import type { LeaveApplication } from "../api/types";

const PENDING = new Set([
  "submitted", "unit_head_review", "recommended", "not_recommended",
  "establishment_review",
]);

export const LeaveApplicationsPage = () => {
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      setApplications(await getApplications());
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function withdraw(id: number) {
    setBusyId(id);
    setError("");
    try {
      await withdrawApplication(id);
      await refresh();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="leave-applications-page">
      <h2>My Leave Applications</h2>
      {error && <p role="alert">{error}</p>}
      {loading ? <p>Loading applications…</p> : applications.length === 0 ? (
        <p>No leave applications yet.</p>
      ) : (
        <table>
          <thead><tr>
            <th>Type</th><th>Period</th><th>Status</th><th>Purpose</th><th>Actions</th>
          </tr></thead>
          <tbody>
            {applications.map((app) => (
              <tr key={app.id}>
                <td>{app.leave_category_code}</td>
                <td>{app.requested_start} – {app.requested_end}</td>
                <td>{app.status.replaceAll("_", " ")}</td>
                <td>{app.purpose}</td>
                <td>
                  <Link to={`/elm/print-application/${app.id}`}>Print</Link>
                  {PENDING.has(app.status) && (
                    <button type="button" disabled={busyId === app.id}
                      onClick={() => void withdraw(app.id)}>
                      {busyId === app.id ? "Withdrawing…" : "Withdraw"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
};
