import { useState } from "react";
import { Button, Card, Container, Group, Stack, Textarea, TextInput } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useLeaves, useSubmitLeave } from "../api/hooks";
import type { Leave } from "../api/types";

const columns = [
  { key: "id", header: "#", render: (r: Leave) => r.id },
  { key: "from", header: "From", render: (r: Leave) => r.from_date },
  { key: "to", header: "To", render: (r: Leave) => r.to_date },
  { key: "status", header: "Status", render: (r: Leave) => <StatusBadge status={r.status} /> },
];

export default function LeavePage() {
  const { data, error, isPending } = useLeaves();
  const submit = useSubmitLeave();
  const [reason, setReason] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [link, setLink] = useState("");

  const onSubmit = () =>
    submit.mutate(
      { reason, from_date: from, to_date: to, supporting_document_link: link },
      {
        onSuccess: () => {
          notifyDone("Leave application submitted.");
          setReason(""); setFrom(""); setTo(""); setLink("");
        },
        onError: notifyError,
      },
    );

  return (
    <Container size="lg" py="md">
      <PageHeader title="Leave" subtitle="Submit a leave application and track its status." />
      <Card withBorder mb="md">
        <Stack gap="sm">
          <Textarea label="Reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
          <Group grow>
            <TextInput label="From" type="date" value={from} onChange={(e) => setFrom(e.currentTarget.value)} required />
            <TextInput label="To" type="date" value={to} onChange={(e) => setTo(e.currentTarget.value)} required />
          </Group>
          <TextInput label="Supporting document (Google Drive link, optional)" value={link} onChange={(e) => setLink(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button onClick={onSubmit} loading={submit.isPending} disabled={!reason || !from || !to}>Submit</Button>
          </Group>
        </Stack>
      </Card>
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={520}
          rowKey={(r) => r.id} empty={{ title: "No leave applications yet." }} />
      )}
    </Container>
  );
}
