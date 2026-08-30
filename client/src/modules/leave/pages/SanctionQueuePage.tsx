import { QueuePage } from "../components/QueuePage";
import { useSanctionDecision, useSanctionQueue } from "../api/hooks";

export default function SanctionQueuePage() {
  const { data, isPending, error } = useSanctionQueue();
  const decide = useSanctionDecision();

  return (
    <QueuePage
      title="Sanction Queue"
      subtitle="Recommended requests awaiting your final decision"
      emptyTitle="No requests await sanction"
      emptyDescription="Recommended and routed requests arrive here."
      rows={data ?? []} loading={isPending} error={error}
      approveLabel="Sanction" refuseLabel="Refuse"
      submitting={decide.isPending}
      onDecide={(id, approve, remark) =>
        decide.mutateAsync({ id, approve, remark })}
    />
  );
}
