import { useEffect, useState } from "react";
import {
  fetchLeaveApplications,
  withdrawLeaveApplication,
  type LeaveApplicationRow,
} from "./api";

function canWithdraw(status: string): boolean {
  const normalized = status.toUpperCase().replace(/[\s-]+/g, "_");
  return (
    normalized === "AWAITING_SUBSTITUTE" ||
    normalized === "AWAITING_APPROVAL"
  );
}

export default function LeaveHistory() {
  const [applications, setApplications] = useState<LeaveApplicationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  async function loadApplications() {
    setLoading(true);
    setError("");

    try {
      const rows = await fetchLeaveApplications();
      setApplications(rows);
    } catch {
      setError("Unable to load leave applications. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadApplications();
  }, []);

  async function handleWithdraw(id: number) {
    if (!window.confirm(`Withdraw leave application #${id}?`)) return;

    setBusyId(id);
    setError("");
    setMessage("");

    try {
      await withdrawLeaveApplication(id);
      setMessage(`Application #${id} withdrawn successfully.`);
      await loadApplications();
    } catch {
      setError("Withdrawal failed. The application may no longer be eligible.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Leave Application History</h1>
        <button
          type="button"
          onClick={() => void loadApplications()}
          disabled={loading}
          className="rounded border px-4 py-2 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {message && (
        <p role="status" className="mb-4 text-green-700">
          {message}
        </p>
      )}

      {error && (
        <div role="alert" className="mb-4 text-red-600">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => void loadApplications()}
            className="mt-2 underline"
          >
            Try again
          </button>
        </div>
      )}

      {loading ? (
        <p role="status">Loading applications...</p>
      ) : applications.length === 0 ? (
        <p>No leave applications found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="p-3">ID</th>
                <th className="p-3">Leave Type</th>
                <th className="p-3">Start Date</th>
                <th className="p-3">End Date</th>
                <th className="p-3">Reason</th>
                <th className="p-3">Status</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((application) => (
                <tr key={application.id} className="border-t">
                  <td className="p-3">{application.id}</td>
                  <td className="p-3">
                    {`Leave type #${application.leave_type}`}
                  </td>
                  <td className="p-3">{application.start_date}</td>
                  <td className="p-3">{application.end_date}</td>
                  <td className="p-3">
                    {application.reason || "-"}
                  </td>
                  <td className="p-3">
                    {application.status.replace(/_/g, " ")}
                  </td>
                  <td className="p-3">
                    {canWithdraw(application.status) ? (
                      <button
                        type="button"
                        onClick={() => void handleWithdraw(application.id)}
                        disabled={busyId !== null}
                        className="rounded border border-red-600 px-3 py-1 text-red-600 disabled:opacity-50"
                      >
                        {busyId === application.id
                          ? "Withdrawing..."
                          : "Withdraw"}
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
