import { QueuePage } from "../components/QueuePage";
import { useReviewDecision, useReviewQueue } from "../api/hooks";

export default function ReviewQueuePage() {
  const { data, isPending, error } = useReviewQueue();
  const decide = useReviewDecision();

  return (
    <QueuePage
      title="Review Queue"
      subtitle="Requests from your unit awaiting your recommendation"
      emptyTitle="Nothing is waiting on you"
      emptyDescription="Requests from your unit appear here as they are submitted."
      rows={data ?? []} loading={isPending} error={error}
      approveLabel="Recommend" refuseLabel="Reject"
      submitting={decide.isPending}
      onDecide={(id, approve, remark) =>
        decide.mutateAsync({ id, approve, remark })}
    />
  );
}
