import { useState } from "react";
import { Badge, Button, Card, Drawer, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { useRequestDetails } from "../api/hooks";

function label(value: string) {
  return value.replaceAll("_", " ");
}

export function RequestDetailsContent({ id }: { id: number }) {
  const { data, error, isPending } = useRequestDetails(id);
  return <Stack>
    {isPending && <Text c="dimmed">Loading request history...</Text>}
    {error && <ErrorState error={error} />}
    {data && <>
      <Badge>{label(data.state)}</Badge>
      <Text fw={600}>Submitted information</Text>
      <Text size="sm" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
        {JSON.stringify(data.appraisal_summary?.submitted_form ?? data.payload, null, 2)}
      </Text>
      <Text fw={600}>Workflow history</Text>
      {data.history.length === 0 && <Text c="dimmed">No workflow history is recorded.</Text>}
      {data.history.map((event, index) => <Card withBorder key={index}>
        <Text fw={600}>{label(event.event)} — {label(event.target)}</Text>
        <Text size="sm">Acting role: {event.acting_designation}</Text>
        {event.reason && <Text size="sm" style={{ overflowWrap: "anywhere" }}>{event.reason}</Text>}
        <Text size="xs" c="dimmed">{new Date(event.recorded_at).toLocaleString()}</Text>
      </Card>)}
      {!!data.claim_summary?.status_history?.length && <>
        <Text fw={600}>Reported financial status history</Text>
        {data.claim_summary.status_history.map((event, index) => <Card withBorder key={index}>
          <Text fw={600}>{label(event.payment_status)}</Text>
          <Text size="sm" style={{ overflowWrap: "anywhere" }}>
            {event.source_system}: {event.external_status_reference}
          </Text>
          <Text size="xs" c="dimmed">{new Date(event.recorded_at).toLocaleString()}</Text>
        </Card>)}
      </>}
    </>}
  </Stack>;
}

export function RequestDetails({ id }: { id: number }) {
  const [opened, setOpened] = useState(false);
  return <>
    <Button size="xs" variant="default" onClick={() => setOpened(true)}>Details</Button>
    <Drawer opened={opened} onClose={() => setOpened(false)} title={`Request #${id} history`}
      position="right" size="lg">
      {opened && <RequestDetailsContent id={id} />}
    </Drawer>
  </>;
}
