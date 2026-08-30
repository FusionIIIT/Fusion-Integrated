import { QueuePage } from "../components/QueuePage";
import { useResumptionQueue, useVerifyResumption } from "../api/hooks";

export default function ResumptionsPage() {
  const { data, isPending, error } = useResumptionQueue();
  const decide = useVerifyResumption();

  return (
    <QueuePage
      title="Resumptions"
      subtitle="Reported returns to duty awaiting verification"
      emptyTitle="Nothing to verify"
      emptyDescription="Resumption reports appear here once employees submit them."
      rows={data ?? []} loading={isPending} error={error}
      approveLabel="Verify" refuseLabel="Query"
      submitting={decide.isPending}
      onDecide={(id, approve, remark) =>
        decide.mutateAsync({ id, approve, remark })}
    />
  );
}
