import { PageHeader } from "../../../ui/components/PageHeader";
import { useOutbox } from "../api/hooks";
import FileRows from "../components/FileRows";
import { FtsError } from "../components/FtsError";

export function OutboxPage() {
  const { data, isPending, error } = useOutbox();
  return (
    <>
      <PageHeader title="Outbox" subtitle="Files you sent that someone else now holds" />
      {error != null ? <FtsError error={error} /> : (
        <FileRows
          rows={data ?? []} loading={isPending}
          emptyTitle="Nothing in your outbox"
          emptyDescription="Files you forward or return will appear here."
        />
      )}
    </>
  );
}

export default OutboxPage;
