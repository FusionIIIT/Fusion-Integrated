import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Select, Stack, Text, Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaGavel, FaInfoCircle } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSanctionClaim } from "../api/hooks";
import type { ReimbursementClaim } from "../api/types";

const DECISIONS = [
  { value: "approve", label: "Approve for payment" },
  { value: "reject", label: "Reject (terminal)" },
];

export default function ApproverSanctionsPage() {
  const { can } = useAuth();
  const canSanction = can("phc.reimbursement.sanction");
  const sanction = useSanctionClaim();
  const [claimId, setClaimId] = useState("");
  const [decision, setDecision] = useState<string | null>("approve");
  const [note, setNote] = useState("");
  const [decided, setDecided] = useState<ReimbursementClaim[]>([]);

  function submit() {
    if (!claimId || !decision) return;
    sanction.mutate(
      {
        id: Number(claimId),
        decision: decision as "approve" | "reject",
        note,
      },
      {
        onSuccess: (claim) => {
          setDecided((prev) => [claim, ...prev]);
          setClaimId("");
          setNote("");
          notifications.show({
            color: claim.state === "rejected" ? "orange" : "green",
            title: "Sanction recorded",
            message: `Claim #${claim.claim_id} is ${claim.state.replace(/_/g, " ")}.`,
          });
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record sanction", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Decide Sanctions"
        subtitle="Final approval or rejection of verified reimbursement claims"
      />

      <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
        <Text size="sm">
          Enter the claim number from the verification note. Rejection is
          terminal: a later claim must be submitted afresh, never reopened.
        </Text>
      </Alert>

      {!canSanction && (
        <Text c="red" size="sm" mb="md">
          You do not have permission to decide sanctions.
        </Text>
      )}
      {sanction.error && <ErrorState error={sanction.error} />}

      {canSanction && (
        <Card padding="lg" mb="md">
          <Stack gap="md">
            <Group grow align="flex-end">
              <TextInput
                label="Claim number" type="number" min={1} required
                value={claimId} placeholder="e.g. 118"
                onChange={(e) => setClaimId(e.currentTarget.value)}
              />
              <Select
                label="Decision" required data={DECISIONS} value={decision}
                onChange={setDecision} allowDeselect={false}
              />
            </Group>
            <Textarea
              label="Decision note" autosize minRows={3} value={note}
              onChange={(e) => setNote(e.currentTarget.value)}
              placeholder="Basis for the sanction decision"
            />
            <Group justify="flex-end">
              <Button
                onClick={submit} loading={sanction.isPending}
                color={decision === "reject" ? "red" : undefined}
                disabled={!claimId || Number(claimId) < 1
                  || (decision !== "approve" && decision !== "reject")}
              >
                Record sanction
              </Button>
            </Group>
          </Stack>
        </Card>
      )}

      <Card padding="lg">
        <DataTable<ReimbursementClaim>
          rows={decided}
          rowKey={(r) => r.claim_id}
          minWidth={760}
          columns={[
            { key: "claim_id", header: "Claim",
              render: (r) => <Text fw={600}>#{r.claim_id}</Text> },
            { key: "amount", header: "Amount", align: "right",
              render: (r) => `₹${r.amount}` },
            { key: "state", header: "State",
              render: (r) => <Badge variant="light">{r.state.replace(/_/g, " ")}</Badge> },
            { key: "stage_actor", header: "Next",
              render: (r) => r.stage_actor || "—" },
          ]}
          empty={{
            icon: FaGavel,
            title: "No sanctions recorded yet",
            description: "Sanctions you decide in this session will be listed here.",
          }}
        />
      </Card>
    </Container>
  );
}
