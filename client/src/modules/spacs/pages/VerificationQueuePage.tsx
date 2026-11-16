import { useVerificationQueue, useVerifyApplication } from "../api/hooks";

export default function VerificationQueuePage() {
  const { data: queue, isLoading, error } = useVerificationQueue();
  const verifyMutation = useVerifyApplication();

  if (isLoading) {
    return <div role="status">Loading verification queue...</div>;
  }

  if (error) {
    return <div role="alert">Failed to load verification queue. Please try again.</div>;
  }

  if (!queue || queue.length === 0) {
    return <div>No applications pending verification.</div>;
  }

  return (
    <div>
      <h1>Verification Queue</h1>
      <ul>
        {queue.map((app) => (
          <li key={app.id}>
            <span>{app.application_id} - Student ID: {app.applicant_user_id}</span>
            <button
              aria-label={`Mark verified for ${app.application_id}`}
              onClick={() => verifyMutation.mutate({ id: app.id, action: "verify" })}
            >
              Verify
            </button>
            <button
              aria-label={`Mark defective for ${app.application_id}`}
              onClick={() => verifyMutation.mutate({ id: app.id, action: "defect", notes: "Incomplete document" })}
            >
              Request Defect Correction
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
