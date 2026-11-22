import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, NumberInput, Stack, Tabs, Text, TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaDoorOpen, FaSignOutAlt, FaUserShield } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCheckOut, useDenials, useOverride, useValidate } from "../api/hooks";
import type { Denial, GateOutcome } from "../api/types";
import { formatDateTime, humanise } from "../format";

const GATE_KEY = "vms.gate_id";

function savedGate(): number | "" {
  try {
    const n = Number(window.localStorage.getItem(GATE_KEY));
    return Number.isInteger(n) && n > 0 ? n : "";
  } catch {
    return "";
  }
}

export default function GatePage() {
  const { can } = useAuth();
  const [credential, setCredential] = useState("");
  const [gateId, setGateId] = useState<number | "">(savedGate);
  const [outcome, setOutcome] = useState<GateOutcome | null>(null);
  const [overriding, setOverriding] = useState<Denial | null>(null);
  const [justification, setJustification] = useState("");
  const validate = useValidate();
  const checkOut = useCheckOut();
  const override = useOverride();
  const denials = useDenials("open");
  const canOverride = can("vms.gate.override");

  const ready = credential.trim().length > 0 && gateId !== "";

  function rememberGate(value: string | number) {
    const next = typeof value === "number" ? value : "";
    setGateId(next);
    try {
      if (next === "") window.localStorage.removeItem(GATE_KEY);
      else window.localStorage.setItem(GATE_KEY, String(next));
    } catch { /* private mode: the gate is simply not remembered */ }
  }

  function enter() {
    if (!ready) return;
    validate.mutate({ credential, gate_id: Number(gateId) }, {
      onSuccess: (res) => { setOutcome(res); if (!res.code) setCredential(""); },
      onError: (e) => setOutcome({ detail: errorMessage(e), code: "error" }),
    });
  }

  function exit() {
    if (credential.trim().length === 0) return;
    checkOut.mutate({ credential, gate_id: gateId === "" ? null : Number(gateId) }, {
      onSuccess: (res) => { setOutcome({ detail: res.detail }); setCredential(""); },
      onError: (e) => setOutcome({ detail: errorMessage(e), code: "error" }),
    });
  }

  function submitOverride() {
    if (!overriding) return;
    override.mutate(
      { denial_log_id: overriding.id, justification: justification.trim() },
      { onSuccess: () => {
        notifications.show({ color: "green", message: `${overriding.visitor_name} may enter.` });
        setOverriding(null);
        setJustification("");
      } },
    );
  }

  const denied = outcome?.code !== undefined;

  return (
    <Container size="md">
      <PageHeader title="Gate" subtitle="Validate a pass to let a visitor in, or check them out" />

      <Tabs defaultValue="scan" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="scan" leftSection={<FaDoorOpen size={12} />}>Entry and exit</Tabs.Tab>
          <Tabs.Tab value="denials" leftSection={<FaUserShield size={12} />}>
            Denied entries {denials.data ? `(${denials.data.results.length})` : ""}
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="scan">
          <Card withBorder padding="lg">
            <Stack>
              <NumberInput
                label="This gate's number" min={1} allowDecimal={false} w={200}
                description="Remembered on this device." value={gateId} onChange={rememberGate}
              />
              <TextInput
                label="Pass QR code or 6-digit OTP" autoFocus value={credential}
                onChange={(e) => setCredential(e.currentTarget.value)}
                onKeyDown={(e) => { if (e.key === "Enter") enter(); }}
              />
              <Group>
                <Button
                  leftSection={<FaDoorOpen size={12} />} disabled={!ready}
                  loading={validate.isPending} onClick={enter}
                >
                  Check in
                </Button>
                <Button
                  variant="default" leftSection={<FaSignOutAlt size={12} />}
                  disabled={credential.trim().length === 0} loading={checkOut.isPending}
                  onClick={exit}
                >
                  Check out
                </Button>
              </Group>
            </Stack>
          </Card>

          {outcome && (
            <Alert
              mt="md" color={denied ? "red" : "green"} variant="light"
              title={denied ? "Entry refused" : outcome.visitor_name ?? "Done"}
            >
              <Text size="sm">{outcome.detail}</Text>
              {outcome.vip_override && <Badge mt={6} color="grape" variant="light">VIP override</Badge>}
              {outcome.override_eligible && (
                <Text size="xs" mt={6}>An Admin can override this refusal.</Text>
              )}
            </Alert>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="denials">
          <DataTable<Denial>
            rows={denials.data?.results ?? []}
            loading={denials.isPending}
            rowKey={(d) => d.id}
            minWidth={560}
            empty={{ title: "No open denials" }}
            columns={[
              { key: "visitor", header: "Visitor", render: (d) => d.visitor_name },
              { key: "why", header: "Reason", render: (d) => d.failures.map(humanise).join(", ") },
              { key: "at", header: "When", render: (d) => formatDateTime(d.created_at) },
              { key: "act", header: "", align: "right", render: (d) => (
                canOverride ? (
                  <Button size="compact-xs" variant="light" onClick={() => setOverriding(d)}>
                    Override
                  </Button>
                ) : null
              ) },
            ]}
          />
        </Tabs.Panel>
      </Tabs>

      <FormModal
        opened={overriding !== null} onClose={() => setOverriding(null)}
        title="Override denied entry" subtitle={overriding?.visitor_name}
        submitLabel="Allow entry" onSubmit={submitOverride} submitting={override.isPending}
        error={override.error} disabled={justification.trim().length === 0}
        disabledReason="A justification is recorded with the override." size="md"
      >
        <Textarea
          label="Justification" required autosize minRows={3} maxLength={500}
          value={justification} onChange={(e) => setJustification(e.currentTarget.value)}
        />
      </FormModal>
    </Container>
  );
}
