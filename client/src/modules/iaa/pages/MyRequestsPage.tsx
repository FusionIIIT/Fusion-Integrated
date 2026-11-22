import { useState } from "react";
import { Button, Container, Text } from "@mantine/core";
import { FaPlus } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecords } from "../api/hooks";
import { NewRecordModal } from "../components/NewRecordModal";
import { RecordDrawer } from "../components/RecordDrawer";
import { RecordTable } from "../components/RecordTable";

export default function MyRequestsPage() {
  const { data, isPending, error } = useRecords();
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  return (
    <Container size="lg">
      <PageHeader title="My requests & TA claims"
        subtitle="Create, submit and track your own items"
        action={<Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
          New</Button>} />
      {isPending ? <Text c="dimmed">Loading…</Text>
        : <RecordTable rows={data?.results ?? []} empty="You have no requests or claims yet"
            onOpen={setOpen} />}
      <NewRecordModal opened={creating} onClose={() => setCreating(false)}
        onCreated={(id) => { setCreating(false); setOpen(id); }} />
      <RecordDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}
