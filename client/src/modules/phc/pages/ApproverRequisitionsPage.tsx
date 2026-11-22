import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Select, Stack, Text, Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClipboardCheck, FaInfoCircle } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideRequisition } from "../api/hooks";
import type { Requisition } from "../api/types";

const DECISIONS = [
  { value: "approve", label: "Approve" },
  { value: "reject", label: "Reject" },
];

export default function ApproverRequisitionsPage() {
  const { can } = useAuth();
  const canDecide = can("phc.requisition.decide");
  const decide = useDecideRequisition();
  const [requisitionId, setRequisitionId] = useState("");
  const [decision, setDecision] = useState<string | null>("approve");
  const [note, setNote] = useState("");
  const [decided, setDecided] = useState<Requisition[]>([]);

  function submit() {
    if (!requisitionId || !decision) return;
    decide.mutate(
      {
        id: Number(requisitionId),
        decision: decision as "approve" | "reject",
        note,
      },
      {
        onSuccess: (requisition) => {
          setDecided((prev) => [requisition, ...prev]);
          setRequisitionId("");
          setNote("");
          notifications.show({
            color: requisition.state === "rejected" ? "orange" : "green",
            title: "Decision recorded",
            message: `Requisition #${requisition.requisition_id} is ${requisition.state.replace(/_/g, " ")}.`,
          });
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record decision", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Decide Requisitions"
        subtitle="Approve or reject pending procurement requisitions"
      />

      <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
        <Text size="sm">
          Decisions are made by requisition number, as printed on the request
          sent to the Approving Authority. The server refuses any number that is
          not still pending.
        </Text>
      </Alert>

      {!canDecide && (
        <Text c="red" size="sm" mb="md">
          You do not have permission to decide requisitions.
        </Text>
      )}
      {decide.error && <ErrorState error={decide.error} />}

      {canDecide && (
        <Card padding="lg" mb="md">
          <Stack gap="md">
            <Group grow align="flex-end">
              <TextInput
                label="Requisition number" type="number" min={1} required
                value={requisitionId} placeholder="e.g. 42"
                onChange={(e) => setRequisitionId(e.currentTarget.value)}
              />
              <Select
                label="Decision" required data={DECISIONS} value={decision}
                onChange={setDecision} allowDeselect={false}
              />
            </Group>
            <Textarea
              label="Decision note" autosize minRows={3} value={note}
              onChange={(e) => setNote(e.currentTarget.value)}
              placeholder="Why this decision was made"
            />
            <Group justify="flex-end">
              <Button
                onClick={submit} loading={decide.isPending}
                color={decision === "reject" ? "red" : undefined}
                disabled={!requisitionId || Number(requisitionId) < 1
                  || (decision !== "approve" && decision !== "reject")}
              >
                Record decision
              </Button>
            </Group>
          </Stack>
        </Card>
      )}

      <Card padding="lg">
        <DataTable<Requisition>
          rows={decided}
          rowKey={(r) => r.requisition_id}
          minWidth={720}
          columns={[
            { key: "id", header: "Requisition",
              render: (r) => <Text fw={600}>#{r.requisition_id}</Text> },
            { key: "state", header: "State",
              render: (r) => <Badge variant="light">{r.state.replace(/_/g, " ")}</Badge> },
            { key: "decided_at", header: "Decided at",
              render: (r) => r.decided_at
                ? new Date(r.decided_at).toLocaleString() : "—" },
            { key: "note", header: "Note",
              render: (r) => r.decision_note || "—" },
          ]}
          empty={{
            icon: FaClipboardCheck,
            title: "No decisions recorded yet",
            description: "Decisions you make in this session will be listed here.",
          }}
        />
      </Card>
    </Container>
  );
}
