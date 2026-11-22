import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaQrcode,
  FaSignInAlt,
  FaSignOutAlt,
  FaUserPlus,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useGateCheckIn,
  useGateCheckOut,
  useGateOverride,
  useLiveVisitors,
  useValidatePass,
  useWalkInRegister,
} from "../api/hooks";
import type { Pass, VisitRequest } from "../api/types";

export default function GatePage() {
  const [tokenInput, setTokenInput] = useState("");
  const [scanResult, setScanResult] = useState<{
    is_valid: boolean;
    message: string;
    pass: Pass | null;
  } | null>(null);

  // Walk-in modal
  const [walkInOpen, setWalkInOpen] = useState(false);
  const [wName, setWName] = useState("");
  const [wEmail, setWEmail] = useState("");
  const [wPhone, setWPhone] = useState("");
  const [wHostId, setWHostId] = useState("1");
  const [wPurpose, setWPurpose] = useState("");
  const [wDocNumber, setWDocNumber] = useState("");

  // Override modal
  const [overridePassId, setOverridePassId] = useState<number | null>(null);
  const [overrideReason, setOverrideReason] = useState("");

  const validatePass = useValidatePass();
  const checkIn = useGateCheckIn();
  const checkOut = useGateCheckOut();
  const gateOverride = useGateOverride();
  const walkInRegister = useWalkInRegister();
  const { data: onsiteVisitors, isPending } = useLiveVisitors();

  function handleScan() {
    if (!tokenInput.trim()) return;
    validatePass.mutate(
      { qr_token: tokenInput.trim(), gate_name: "Main Gate" },
      {
        onSuccess: (data) => {
          setScanResult(data);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Validation Error",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleCheckIn(passId: number) {
    checkIn.mutate(
      { pass_id: passId, gate_name: "Main Gate" },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Checked In",
            message: "Visitor admitted to campus.",
          });
          setScanResult(null);
          setTokenInput("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Check-in Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleCheckOut(passId: number) {
    checkOut.mutate(
      { pass_id: passId, gate_name: "Main Exit Gate" },
      {
        onSuccess: () => {
          notifications.show({
            color: "blue",
            title: "Checked Out",
            message: "Visitor checkout recorded.",
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Checkout Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleOverrideSubmit() {
    if (!overridePassId) return;
    gateOverride.mutate(
      { pass_id: overridePassId, reason: overrideReason, gate_name: "Main Gate Override" },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Override Executed",
            message: "Visitor admitted under manual override.",
          });
          setOverridePassId(null);
          setOverrideReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Override Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleWalkInSubmit() {
    walkInRegister.mutate(
      {
        name: wName,
        email: wEmail,
        phone: wPhone,
        host_id: parseInt(wHostId, 10),
        purpose: wPurpose,
        id_document_type: "AADHAAR",
        id_document_number: wDocNumber,
        auto_approve: true,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Walk-in Registered",
            message: `Admitted ${wName}.`,
          });
          setWalkInOpen(false);
          setWName("");
          setWEmail("");
          setWPhone("");
          setWPurpose("");
          setWDocNumber("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Walk-in Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Security Gate Scanner & Access Control"
          subtitle="Validate passes, admit verified guests, record exits, and process walk-ins."
          action={
            <Button leftSection={<FaUserPlus />} color="teal" onClick={() => setWalkInOpen(true)}>
              Register Walk-in Guest
            </Button>
          }
        />

        {/* Scanner Bar */}
        <Card withBorder padding="md" radius="md">
          <Stack gap="sm">
            <Text fw={600} size="sm">
              Pass QR Token Scanner
            </Text>
            <Group>
              <TextInput
                placeholder="Scan QR code or paste security token (e.g. VMS-PASS-TOKEN)..."
                leftSection={<FaQrcode />}
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                style={{ flex: 1 }}
              />
              <Button loading={validatePass.isPending} onClick={handleScan}>
                Validate Pass
              </Button>
            </Group>

            {scanResult && (
              <Alert
                color={scanResult.is_valid ? "green" : "red"}
                icon={scanResult.is_valid ? <FaCheckCircle /> : <FaExclamationTriangle />}
                title={scanResult.is_valid ? "Pass Verified & Valid" : "Pass Verification Denied"}
              >
                <Group justify="space-between" align="center">
                  <Text size="sm">{scanResult.message}</Text>
                  {scanResult.is_valid && scanResult.pass && (
                    <Button
                      size="xs"
                      color="green"
                      leftSection={<FaSignInAlt />}
                      loading={checkIn.isPending}
                      onClick={() => handleCheckIn(scanResult.pass!.id)}
                    >
                      Admit / Check In
                    </Button>
                  )}
                  {!scanResult.is_valid && scanResult.pass && (
                    <Button
                      size="xs"
                      color="yellow"
                      variant="outline"
                      onClick={() => setOverridePassId(scanResult.pass!.id)}
                    >
                      Authorize Manual Override
                    </Button>
                  )}
                </Group>
              </Alert>
            )}
          </Stack>
        </Card>

        <Divider label="Currently On-site Visitors" labelPosition="center" />

        <DataTable
          loading={isPending}
          rows={onsiteVisitors ?? []}
          rowKey={(v) => v.id}
          empty={{ title: "No visitors currently on campus." }}
          columns={[
            {
              key: "visitor",
              header: "On-site Visitor",
              render: (v: VisitRequest) => (
                <Stack gap={2}>
                  <Text fw={600}>{v.visitor.name}</Text>
                  <Text size="xs" c="dimmed">
                    {v.visitor.phone} • {v.visitor.id_document_type} #{v.visitor.id_document_number}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "checkin",
              header: "Check-in Time",
              render: (v: VisitRequest) => (
                <Text size="sm">
                  {v.actual_check_in ? new Date(v.actual_check_in).toLocaleTimeString() : "N/A"}
                </Text>
              ),
            },
            {
              key: "host",
              header: "Host & Purpose",
              render: (v: VisitRequest) => (
                <Stack gap={2}>
                  <Text size="sm">{v.purpose}</Text>
                  <Text size="xs" c="dimmed">
                    Host #{v.host_id}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "zones",
              header: "Zones Allowed",
              render: (v: VisitRequest) => (
                <Group gap={4}>
                  {v.access_zones?.map((z) => (
                    <Badge key={z} size="xs" variant="light">
                      {z}
                    </Badge>
                  ))}
                </Group>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (v: VisitRequest) =>
                v.digital_pass ? (
                  <Button
                    size="xs"
                    color="gray"
                    variant="light"
                    leftSection={<FaSignOutAlt />}
                    loading={checkOut.isPending}
                    onClick={() => handleCheckOut(v.digital_pass!.id)}
                  >
                    Check Out
                  </Button>
                ) : null,
            },
          ]}
        />

        {/* Modal: Manual Override */}
        <Modal
          opened={!!overridePassId}
          onClose={() => setOverridePassId(null)}
          title="Manual Gate Override Authorization"
          size="sm"
        >
          <Stack gap="sm">
            <Text size="sm">Provide justification for manually admitting this pass:</Text>
            <TextInput
              placeholder="e.g. Phone battery died, ID physically inspected and verified"
              required
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setOverridePassId(null)}>
                Cancel
              </Button>
              <Button
                color="yellow"
                loading={gateOverride.isPending}
                onClick={handleOverrideSubmit}
              >
                Confirm Override
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Walk-in Registration */}
        <Modal
          opened={walkInOpen}
          onClose={() => setWalkInOpen(false)}
          title="Gate Walk-in Registration"
          size="md"
        >
          <Stack gap="sm">
            <TextInput
              label="Guest Full Name"
              required
              value={wName}
              onChange={(e) => setWName(e.target.value)}
            />
            <TextInput
              label="Email Address"
              required
              type="email"
              value={wEmail}
              onChange={(e) => setWEmail(e.target.value)}
            />
            <TextInput
              label="Phone Number"
              required
              value={wPhone}
              onChange={(e) => setWPhone(e.target.value)}
            />
            <TextInput
              label="ID Document Number (Aadhaar / Driving License)"
              required
              value={wDocNumber}
              onChange={(e) => setWDocNumber(e.target.value)}
            />
            <TextInput
              label="Visiting Host Staff ID"
              required
              value={wHostId}
              onChange={(e) => setWHostId(e.target.value)}
            />
            <TextInput
              label="Purpose of Visit"
              required
              value={wPurpose}
              onChange={(e) => setWPurpose(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setWalkInOpen(false)}>
                Cancel
              </Button>
              <Button color="teal" loading={walkInRegister.isPending} onClick={handleWalkInSubmit}>
                Admit Walk-in Guest
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
