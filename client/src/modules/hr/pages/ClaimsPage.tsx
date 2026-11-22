import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Select, Stack, Table,
  Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useClaims, useDecideClaim, useProcessClaim, useRecordIntegration,
  useSubmitClaim, useVerifyClaim,
} from "../api/hooks";
import type { Claim } from "../api/types";

export default function ClaimsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useClaims();
  const [creating, setCreating] = useState(false);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="HR Claims" subtitle="LTC and CPDA claims and approvals"
        action={can("hr.claim.create") && <Button onClick={() => setCreating(true)}>Submit claim</Button>} />
      <Card withBorder>
        {isPending ? <Text>Loading claims…</Text> : data?.results.length ? (
          <Table.ScrollContainer minWidth={900}><Table striped>
            <Table.Thead><Table.Tr>
              <Table.Th>Claim</Table.Th><Table.Th>Employee</Table.Th><Table.Th>Purpose</Table.Th>
              <Table.Th>Amount</Table.Th><Table.Th>Status</Table.Th><Table.Th>Submitted</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>{data.results.map((claim) => (
              <Table.Tr key={claim.id}>
                <Table.Td>#{claim.id}<Text size="xs" c="dimmed">{claim.request_type_display}</Text></Table.Td>
                <Table.Td>{claim.employee_user_id}</Table.Td><Table.Td>{claim.purpose || "—"}</Table.Td>
                <Table.Td>{claim.amount ?? "—"}</Table.Td><Table.Td><Badge>{claim.status_display}</Badge></Table.Td>
                <Table.Td>{new Date(claim.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td><ClaimActions claim={claim} /></Table.Td>
              </Table.Tr>
            ))}</Table.Tbody>
          </Table></Table.ScrollContainer>
        ) : <Text c="dimmed">No claims are available.</Text>}
      </Card>
      {creating && <ClaimEditor onClose={() => setCreating(false)} />}
    </Container>
  );
}

function ClaimActions({ claim }: { claim: Claim }) {
  const { can, session } = useAuth();
  const verify = useVerifyClaim(claim.id);
  const decide = useDecideClaim(claim.id);
  const [processing, setProcessing] = useState(false);
  const [integration, setIntegration] = useState(false);
  const [note, setNote] = useState("");
  const onSuccess = (title: string) => () =>
    notifications.show({ color: "green", title, message: "Claim updated." });
  const onError = (e: unknown) =>
    notifications.show({ color: "red", title: "Action failed", message: errorMessage(e) });
  const mine = claim.current_authority_user_id === session?.user.id;
  return (
    <Stack gap={4}>
      {can("hr.claim.verify") && claim.status === "pending_verification" && (
        <>
          <TextInput aria-label="Verification note" placeholder="Verification note" value={note}
            onChange={(e) => setNote(e.currentTarget.value)} />
          <Group gap={4}>
            <Button size="xs" loading={verify.isPending} onClick={() => verify.mutate(
              { verified: true, note }, { onSuccess: onSuccess("Claim verified"), onError })}>Verify</Button>
            <Button size="xs" variant="light" color="red" loading={verify.isPending} onClick={() => verify.mutate(
              { verified: false, note }, { onSuccess: onSuccess("Verification recorded"), onError })}>Unable to verify</Button>
          </Group>
        </>
      )}
      {can("hr.claim.approve") && mine &&
        claim.employee_user_id !== session?.user.id &&
        ["pending_authority", "pending_next_authority"].includes(claim.status) && (
          <>
            <TextInput aria-label="Decision note" placeholder="Decision note" value={note}
              onChange={(e) => setNote(e.currentTarget.value)} />
            <Group gap={4}>{(["approve", "reject", "forward"] as const).map((action) => (
              <Button key={action} size="xs" loading={decide.isPending}
                color={action === "reject" ? "red" : undefined}
                onClick={() => decide.mutate({ action, note }, {
                  onSuccess: onSuccess(action === "forward" ? "Claim forwarded"
                    : action === "approve" ? "Claim approved" : "Claim rejected"),
                  onError,
                })}>{action}</Button>
            ))}</Group>
          </>
        )}
      {can("hr.claim.manage") && claim.status === "approved" &&
        <Button size="xs" onClick={() => setProcessing(true)}>Record processing</Button>}
      {can("hr.claim.manage") && ["approved", "financial_processing_recorded"].includes(claim.status) &&
        <Button size="xs" variant="light" onClick={() => setIntegration(true)}>Record external status</Button>}
      {claim.integration_statuses.map((entry) =>
        <Text key={entry.id} size="xs">{entry.system}: {entry.external_status}</Text>)}
      {processing && <ProcessingEditor claimId={claim.id} onClose={() => setProcessing(false)} />}
      {integration && <IntegrationEditor claimId={claim.id} onClose={() => setIntegration(false)} />}
    </Stack>
  );
}

function ClaimEditor({ onClose }: { onClose: () => void }) {
  const submit = useSubmitClaim();
  const [type, setType] = useState<Claim["request_type"]>("ltc_advance");
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");
  const [formData, setFormData] = useState("{}");
  const [links, setLinks] = useState("");
  function save() {
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(formData) as Record<string, unknown>;
      if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Enter a JSON object.");
    } catch (e) {
      notifications.show({ color: "red", title: "Invalid form information", message: e instanceof Error ? e.message : errorMessage(e) });
      return;
    }
    submit.mutate({
      request_type: type, purpose, amount: amount || null, form_data: data,
      supporting_document_links: links.split(/\r?\n/).map((url) => url.trim()).filter(Boolean),
    }, {
      onSuccess: () => { notifications.show({ color: "green", title: "Claim submitted", message: "Your claim was submitted for verification." }); onClose(); },
      onError: (e) => notifications.show({ color: "red", title: "Could not submit claim", message: errorMessage(e) }),
    });
  }
  return <Modal opened onClose={onClose} title="Submit LTC or CPDA claim" size="lg">
    <Stack>
      <Select label="Claim type" value={type} onChange={(value) => value && setType(value as Claim["request_type"])}
        data={[
          { value: "ltc_advance", label: "LTC advance" },
          { value: "ltc_reimbursement", label: "LTC reimbursement" },
          { value: "cpda_advance", label: "CPDA advance" },
          { value: "cpda_reimbursement", label: "CPDA reimbursement" },
        ]} />
      <TextInput label="Purpose" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} />
      <TextInput label="Amount (required for CPDA)" type="number" min="0.01"
        value={amount} onChange={(e) => setAmount(e.currentTarget.value)} />
      <Textarea label="Prescribed form information (JSON)" minRows={5} value={formData}
        onChange={(e) => setFormData(e.currentTarget.value)} />
      <Textarea label="Supporting Google Drive document links (one per line)" minRows={3} value={links}
        onChange={(e) => setLinks(e.currentTarget.value)} />
      <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancel</Button>
        <Button loading={submit.isPending} onClick={save}>Submit claim</Button></Group>
    </Stack>
  </Modal>;
}

function ProcessingEditor({ claimId, onClose }: { claimId: number; onClose: () => void }) {
  const mutation = useProcessClaim(claimId);
  const [details, setDetails] = useState("{}");
  function save() {
    try {
      const value = JSON.parse(details) as Record<string, unknown>;
      if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("Enter a JSON object.");
      mutation.mutate({ financially_correct: true, details: value }, {
        onSuccess: () => { notifications.show({ color: "green", title: "Processing recorded", message: "Financial processing details were recorded." }); onClose(); },
        onError: (e) => notifications.show({ color: "red", title: "Could not record processing", message: errorMessage(e) }),
      });
    } catch (e) {
      notifications.show({ color: "red", title: "Invalid processing details", message: e instanceof Error ? e.message : errorMessage(e) });
    }
  }
  return <Modal opened onClose={onClose} title="Record financial processing"><Stack>
    <Textarea label="Processing details (JSON)" value={details} minRows={5}
      onChange={(e) => setDetails(e.currentTarget.value)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancel</Button>
      <Button loading={mutation.isPending} onClick={save}>Confirm and record</Button></Group>
  </Stack></Modal>;
}

function IntegrationEditor({ claimId, onClose }: { claimId: number; onClose: () => void }) {
  const mutation = useRecordIntegration(claimId);
  const [system, setSystem] = useState("payroll");
  const [externalStatus, setExternalStatus] = useState("");
  const [reference, setReference] = useState("");
  return <Modal opened onClose={onClose} title="Record external status"><Stack>
    <Select label="System" value={system} onChange={(value) => value && setSystem(value)}
      data={["payroll", "finance"]} />
    <TextInput label="External status" required value={externalStatus}
      onChange={(e) => setExternalStatus(e.currentTarget.value)} />
    <TextInput label="External reference" value={reference}
      onChange={(e) => setReference(e.currentTarget.value)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancel</Button>
      <Button loading={mutation.isPending} disabled={!externalStatus.trim()}
        onClick={() => mutation.mutate({ system, external_status: externalStatus,
          external_reference: reference, details: {} }, {
          onSuccess: () => { notifications.show({ color: "green", title: "Status recorded", message: "The external status was recorded." }); onClose(); },
          onError: (e) => notifications.show({ color: "red", title: "Could not record status", message: errorMessage(e) }),
        })}>Save status</Button></Group>
  </Stack></Modal>;
}