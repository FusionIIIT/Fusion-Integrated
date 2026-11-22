import { useState } from "react";
import { Container, SegmentedControl, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecords } from "../api/hooks";
import { RecordDrawer } from "../components/RecordDrawer";
import { RecordTable } from "../components/RecordTable";

export default function FinanceReviewPage() {
  const [queue, setQueue] = useState("finance_review");
  const { data, isPending, error } = useRecords({ queue });
  const [open, setOpen] = useState<number | null>(null);
  return (
    <Container size="lg">
      <PageHeader title="Finance review"
        subtitle="Validate requests, verify TA claims and record approved items" />
      <Stack gap="md">
        <SegmentedControl value={queue} onChange={setQueue}
          data={[{ value: "finance_review", label: "To review" },
                 { value: "to_record", label: "To record" }]} />
        {error && <ErrorState error={error} />}
        {isPending ? <Text c="dimmed">Loading…</Text>
          : <RecordTable rows={data?.results ?? []} empty="Nothing is waiting here"
              onOpen={setOpen} />}
      </Stack>
      <RecordDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}
