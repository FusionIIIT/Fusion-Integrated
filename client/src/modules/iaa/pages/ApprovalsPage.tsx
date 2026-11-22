import { useState } from "react";
import { Container, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecords } from "../api/hooks";
import { RecordDrawer } from "../components/RecordDrawer";
import { RecordTable } from "../components/RecordTable";

export default function ApprovalsPage() {
  const { data, isPending, error } = useRecords({ queue: "pending_approval" });
  const [open, setOpen] = useState<number | null>(null);
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  return (
    <Container size="lg">
      <PageHeader title="Approvals"
        subtitle="Items waiting on your active role; every decision needs remarks" />
      {isPending ? <Text c="dimmed">Loading…</Text>
        : <RecordTable rows={data?.results ?? []} empty="Nothing is waiting on your role"
            onOpen={setOpen} />}
      <RecordDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}
