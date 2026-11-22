import { useMemo, useState } from "react";
import {
  Button, Card, Container, Group, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCreditCard, FaSearch } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLog, useProcessPayment } from "../api/hooks";
import type { AuditLog } from "../api/types";

interface ClaimRow {
  claim_id: number;
  action: string;
  actor_role: string;
  created_at: string;
}

export default function AuditPaymentsPage() {
  const { can } = useAuth();
  const canPay = can("phc.reimbursement.payment");
  const audit = useAuditLog(100);
  const pay = useProcessPayment();
  const [claimId, setClaimId] = useState("");
  const [reference, setReference] = useState("");

  const rows = useMemo<ClaimRow[]>(() => {
    const latest = new Map<number, AuditLog>();
    for (const entry of audit.data?.results ?? []) {
      if (entry.target_type === "claim" && !latest.has(entry.target_id)) {
        latest.set(entry.target_id, entry);
      }
    }
    return [...latest.values()]
      .filter((entry) => entry.detail?.state === "approved_for_payment")
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

  function doPay(id: number, note: string) {
    pay.mutate(
      { id, note },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Payment processed",
            message: `Claim #${id} is now reimbursed.`,
          });
          setClaimId("");
          setReference("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not process payment", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Process Payments"
        subtitle="Sanctioned claims ready for final reimbursement"
      />

      {!canPay && (
        <Text c="red" size="sm" mb="md">
          You do not have permission to process payments.
        </Text>
      )}
      {pay.error && <ErrorState error={pay.error} />}

      {canPay && (
        <Card padding="lg" mb="md">
          <Group align="flex-end" grow>
            <TextInput
              label="Claim number" type="number" min={1} value={claimId}
              onChange={(e) => setClaimId(e.currentTarget.value)}
              placeholder="Approved claim id" w={220}
            />
            <TextInput
              label="Payment reference" value={reference}
              onChange={(e) => setReference(e.currentTarget.value)}
              placeholder="Voucher or transaction reference"
            />
            <Button
              leftSection={<FaSearch size={11} />} loading={pay.isPending}
              onClick={() => doPay(Number(claimId), reference)}
              disabled={!claimId || Number(claimId) < 1}
            >
              Process by number
            </Button>
          </Group>
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
              key: "pay", header: "", align: "right",
              render: (r) => canPay && (
                <Button
                  size="xs" variant="light"
                  leftSection={<FaCreditCard size={11} />}
                  loading={pay.isPending}
                  onClick={() => doPay(r.claim_id, "")}
                >
                  Process payment
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaCreditCard,
            title: "No claims ready for payment",
            description: "Claims approved at sanction will appear here.",
          }}
        />
      </Card>

      <Text size="xs" c="dimmed" mt="sm">
        Payment is recorded against the claim id and appended to the immutable
        audit trail. The server refuses a claim that is not approved for payment.
      </Text>
    </Container>
  );
}
