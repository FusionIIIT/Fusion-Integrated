import { useApplications, useRecordDecision } from "../api/hooks";

export default function DecisionsPage() {
  const { data: applications, isLoading, error } = useApplications();
  const decisionMutation = useRecordDecision();

  if (isLoading) {
    return <div role="status">Loading pending decisions...</div>;
  }

  if (error) {
    return <div role="alert">Failed to load decisions. Please try again.</div>;
  }

  const pending = (applications ?? []).filter(
    (a) => a.state === "verified" || a.state === "under_convener_review"
  );

  if (pending.length === 0) {
    return <div>No applications currently awaiting decision.</div>;
  }

  return (
    <div>
      <h1>Scholarship Decisions</h1>
      <ul>
        {pending.map((app) => (
          <li key={app.id}>
            <span>{app.application_id} ({app.academic_cycle})</span>
            <button
              aria-label={`Approve application ${app.application_id}`}
              onClick={() => decisionMutation.mutate({ application_id: app.application_id, outcome: "approved" })}
            >
              Approve Scholarship
            </button>
            <button
              aria-label={`Reject application ${app.application_id}`}
              onClick={() => decisionMutation.mutate({ application_id: app.application_id, outcome: "rejected", reason: "Criteria unmet" })}
            >
              Reject
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
