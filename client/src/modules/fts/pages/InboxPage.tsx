import { PageHeader } from "../../../ui/components/PageHeader";
import { useInbox } from "../api/hooks";
import FileRows from "../components/FileRows";
import { FtsError } from "../components/FtsError";

export function InboxPage() {
  const { data, isPending, error } = useInbox();
  return (
    <>
      <PageHeader title="Inbox" subtitle="Files currently held by you" />
      {error != null ? <FtsError error={error} /> : (
        <FileRows
          rows={data ?? []} loading={isPending}
          emptyTitle="Your inbox is empty"
          emptyDescription="Files sent to you will appear here."
        />
      )}
    </>
  );
}

export default InboxPage;
