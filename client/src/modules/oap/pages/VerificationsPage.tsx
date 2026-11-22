import { Button, Container, Group } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { notifyDone, notifyError } from "../components/notify";
import { useClaims, useVerifyClaim } from "../api/hooks";
import type { Claim } from "../api/types";

export default function VerificationsPage() {
  const { data, error, isPending } = useClaims();
  const { session } = useAuth();
  const verify = useVerifyClaim();
  const me = session?.user.id;

  const action = (c: Claim) => {
    const recorded = new Set(c.verifications.map((v) => v.role));
    const slots: { role: "thesis" | "ta"; label: string }[] = [];
    if (c.thesis_supervisor_user_id === me && !recorded.has("thesis")) slots.push({ role: "thesis", label: "Verify as thesis supervisor" });
    if (c.ta_supervisor_user_id === me && !recorded.has("ta")) slots.push({ role: "ta", label: "Verify as TA supervisor" });
    if (!slots.length) return null;
    return (
      <Group gap="xs" justify="flex-end">
        {slots.map((s) => (
          <Button key={s.role} size="xs" onClick={() => verify.mutate({ id: c.id, role: s.role }, {
            onSuccess: () => notifyDone("Verification recorded."), onError: notifyError })}>{s.label}</Button>
        ))}
      </Group>
    );
  };

  const columns = [
    { key: "id", header: "Claim", render: (r: Claim) => `#${r.id}` },
    { key: "done", header: "Recorded", render: (r: Claim) => r.verifications.map((v) => v.role).join(", ") || "none" },
    { key: "act", header: "Action", align: "right" as const, render: action },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Verifications" subtitle="Claims that name you as a supervisor." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={560}
          rowKey={(r) => r.id} empty={{ title: "No claims name you as a supervisor." }} />
      )}
    </Container>
  );
}
