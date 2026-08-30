import { QueuePage } from "../components/QueuePage";
import { useRoute, useRoutingQueue } from "../api/hooks";

export default function RoutingQueuePage() {
  const { data, isPending, error } = useRoutingQueue();
  const route = useRoute();

  return (
    <QueuePage
      title="Routing Queue"
      subtitle="Recommended requests to forward to the competent authority"
      emptyTitle="Nothing to route"
      emptyDescription="Requests recommended by a unit head arrive here."
      rows={data ?? []} loading={isPending} error={error}
      // The establishment forwards; it does not decide, so there is no refusal.
      approveLabel="Forward"
      submitting={route.isPending}
      onDecide={(id, _approve, remark) => route.mutateAsync({ id, remark })}
    />
  );
}
