import { useMemo, useState } from "react";
import {
  Badge, Button, Card, Container, Group, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaSearch } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLog, useVerifyClaim } from "../api/hooks";
import type { AuditLog } from "../api/types";

interface ClaimRow {
  claim_id: number;
  action: string;
  actor_role: string;
  created_at: string;
}

export default function AuditVerifyPage() {
  const { can } = useAuth();
  const canVerify = can("phc.reimbursement.verify");
  const audit = useAuditLog(100);
  const verify = useVerifyClaim();
  const [claimId, setClaimId] = useState("");
  const [note, setNote] = useState("");

  const rows = useMemo<ClaimRow[]>(() => {
    const latest = new Map<number, AuditLog>();
    for (const entry of audit.data?.results ?? []) {
      if (entry.target_type === "claim" && !latest.has(entry.target_id)) {
        latest.set(entry.target_id, entry);
      }
    }
    return [...latest.values()]
      .filter((entry) => entry.detail?.state === "pending_audit")
      .map((entry) => ({
        claim_id: entry.target_id,
        action: entry.action,
        actor_role: entry.actor_role,
        created_at: entry.created_at,
      }));
  }, [audit.data]);

  if (audit.error) {
    return <Container size="lg"><ErrorState error={audit.error} /></Container>;
  }

  function doVerify(id: number, why: string) {
    verify.mutate(
      { id, note: why },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Claim verified",
            message: `Claim #${id} has been sent for sanction.`,
          });
          setClaimId("");
          setNote("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not verify claim", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Verify Claims"
        subtitle="Claims awaiting Accounts & Audit financial verification"
      />

      {!canVerify && (
        <Text c="red" size="sm" mb="md">
          You do not have permission to verify claims.
        </Text>
      )}

      {verify.error && <ErrorState error={verify.error} />}

      {canVerify && (
        <Card padding="lg" mb="md">
          <Stack gap="md">
            <Group align="flex-end" grow>
              <TextInput
                label="Claim number" type="number" min={1} value={claimId}
                onChange={(e) => setClaimId(e.currentTarget.value)}
                placeholder="From the PHC review note" w={220}
              />
              <TextInput
                label="Note (optional)" value={note}
                onChange={(e) => setNote(e.currentTarget.value)}
                placeholder="Verification reference"
              />
              <Button
                leftSection={<FaSearch size={11} />} loading={verify.isPending}
                onClick={() => doVerify(Number(claimId), note)}
                disabled={!claimId || Number(claimId) < 1}
              >
                Verify by number
              </Button>
            </Group>
          </Stack>
        </Card>
      )}

      <Card padding="lg">
        <DataTable<ClaimRow>
          rows={rows}
          loading={audit.isPending}
          rowKey={(r) => r.claim_id}
          minWidth={760}
          columns={[
            { key: "claim_id", header: "Claim",
              render: (r) => <Text fw={600}>#{r.claim_id}</Text> },
            { key: "action", header: "Last recorded action",
              render: (r) => <Text size="sm">{r.action}</Text> },
            { key: "actor_role", header: "From",
              render: (r) => r.actor_role || "—" },
            { key: "created_at", header: "At",
              render: (r) => new Date(r.created_at).toLocaleString() },
            {
              key: "verify", header: "", align: "right",
              render: (r) => canVerify && (
                <Button
                  size="xs" leftSection={<FaCheckCircle size={11} />}
                  loading={verify.isPending}
                  onClick={() => doVerify(r.claim_id, "")}
                >
                  Verify
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaCheckCircle,
            title: "No claims awaiting verification",
            description: "Claims forwarded by PHC review will appear here.",
          }}
        />
      </Card>

      <Text size="xs" c="dimmed" mt="sm">
        <Badge variant="light" size="sm" mr={6}>source</Badge>
        Worklist built from the most recent audit entry for each claim. The
        server re-checks the claim stage before any verification is accepted.
      </Text>
    </Container>
  );
}
