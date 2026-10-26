import { useState } from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { decideAuthority, useAuthorityApprovalsQueue } from "../api/hooks";

export function AuthorityApprovalsPage() {
  const { requests, loading, error, refetch } = useAuthorityApprovalsQueue();
  const [remarks, setRemarks] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);

  const decide = async (id: string, approve: boolean) => {
    setActionError(null);
    try {
      await decideAuthority(id, approve, remarks[id] || "");
      await refetch();
    } catch (err: any) {
      const responseError = err?.response?.data?.error;
      setActionError(responseError?.message ?? responseError ?? err.message ?? "Decision failed.");
    }
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <PageHeader title="Final Sanctioning Queue" subtitle="Make final decisions on higher-sanction leave requests" />
      {loading && <p>Loading sanctioning queue...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}
      {actionError && <p style={{ color: "#dc2626" }}>{actionError}</p>}
      {!loading && requests.length === 0 && <p>No requests are awaiting final sanction.</p>}
      {requests.map((request) => (
        <section key={request.id} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: "1.25rem", marginBottom: "1rem" }}>
          <strong>{request.applicant_user_id} · {request.leave_type} · {request.duration_days} days</strong>
          <p>{request.start_date} to {request.end_date}</p>
          <p>{request.reason}</p>
          <p>Unit Head: {request.action_logs?.filter((log) => ["RECOMMEND", "NOT_RECOMMEND"].includes(log.action)).at(-1)?.action === "NOT_RECOMMEND" ? "Not recommended" : "Recommended"}</p>
          <input
            aria-label={`Decision remarks for ${request.id}`}
            placeholder="Decision remarks"
            value={remarks[request.id] || ""}
            onChange={(event) => setRemarks({ ...remarks, [request.id]: event.target.value })}
          />
          <button onClick={() => decide(request.id, true)}>Approve</button>
          <button onClick={() => decide(request.id, false)}>Reject</button>
        </section>
      ))}
    </div>
  );
}
