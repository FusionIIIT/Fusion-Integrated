import { useState } from "react";
import { Button, Container, Group, TextInput } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useBonafides, useRequestBonafide } from "../api/hooks";
import type { Bonafide } from "../api/types";

export default function BonafidePage() {
  const { data, error, isPending } = useBonafides();
  const request = useRequestBonafide();
  const [purpose, setPurpose] = useState("");

  const columns = [
    { key: "id", header: "#", render: (r: Bonafide) => r.id },
    { key: "purpose", header: "Purpose", render: (r: Bonafide) => r.purpose || "—" },
    { key: "status", header: "Status", render: (r: Bonafide) => <StatusBadge status={r.status} /> },
    {
      key: "cert", header: "Certificate", align: "right" as const,
      render: (r: Bonafide) => (r.status === "approved" ? "Available" : "—"),
    },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Bonafide certificates" subtitle="Request a bonafide certificate and track it." />
      <Group align="flex-end" mb="md">
        <TextInput label="Purpose" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} />
        <Button loading={request.isPending} onClick={() => request.mutate(purpose, {
          onSuccess: () => { notifyDone("Bonafide request submitted."); setPurpose(""); },
          onError: notifyError,
        })}>Request</Button>
      </Group>
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={640}
          rowKey={(r) => r.id} empty={{ title: "No bonafide requests yet." }} />
      )}
    </Container>
  );
}
