import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Code,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaQrcode, FaSearch, FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePreRegisterVisit, useVisits } from "../api/hooks";
import type { VisitRequest } from "../api/types";

const STATUS_COLOR: Record<string, string> = {
  PENDING_APPROVAL: "yellow",
  APPROVED: "blue",
  CHECKED_IN: "green",
  CHECKED_OUT: "gray",
  AUTO_CHECKED_OUT: "orange",
  REJECTED: "red",
  EXPIRED: "dark",
  TERMINATED_EARLY: "red",
};

export default function PassesPage() {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [registering, setRegistering] = useState(false);
  const [viewingPass, setViewingPass] = useState<VisitRequest | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [hostId, setHostId] = useState("1");
  const [purpose, setPurpose] = useState("");
  const [docType, setDocType] = useState("AADHAAR");
  const [docNumber, setDocNumber] = useState("");
  const [hoursAdvance, setHoursAdvance] = useState("3");

  const { data: visits, isPending, error } = useVisits({
    status: statusFilter || undefined,
    search: search || undefined,
  });

  const preRegister = usePreRegisterVisit();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleRegister() {
    const now = new Date();
    const start = new Date(now.getTime() + parseInt(hoursAdvance, 10) * 3600000);
    const end = new Date(start.getTime() + 4 * 3600000);

    preRegister.mutate(
      {
        name,
        email,
        phone,
        host_id: parseInt(hostId, 10),
        purpose,
        id_document_type: docType,
        id_document_number: docNumber,
        scheduled_start: start.toISOString(),
        scheduled_end: end.toISOString(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Pre-registration Submitted",
            message: `Visit request registered for ${name}.`,
          });
          setRegistering(false);
          setName("");
          setEmail("");
          setPhone("");
          setPurpose("");
          setDocNumber("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Registration Failed",
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
          title="Visitor Passes"
          subtitle="View authoritative visitor passes, track status, and pre-register guests."
          action={
            <Button leftSection={<FaPlus />} onClick={() => setRegistering(true)}>
              Pre-register Visitor
            </Button>
          }
        />

        <Group justify="space-between">
          <TextInput
            placeholder="Search visitor by name..."
            leftSection={<FaSearch />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            w={300}
          />
          <Select
            placeholder="Filter by Status"
            clearable
            value={statusFilter}
            onChange={setStatusFilter}
            data={[
              { value: "PENDING_APPROVAL", label: "Pending Approval" },
              { value: "APPROVED", label: "Approved" },
              { value: "CHECKED_IN", label: "Checked In (On-site)" },
              { value: "CHECKED_OUT", label: "Checked Out" },
              { value: "REJECTED", label: "Rejected" },
              { value: "AUTO_CHECKED_OUT", label: "Auto Checked Out" },
            ]}
          />
        </Group>

        <DataTable
          loading={isPending}
          rows={visits ?? []}
          rowKey={(v) => v.id}
          empty={{ title: "No visitor passes found." }}
          columns={[
            {
              key: "visitor",
              header: "Visitor",
              render: (v: VisitRequest) => (
                <Stack gap={2}>
                  <Text fw={500}>{v.visitor.name}</Text>
                  <Text size="xs" c="dimmed">{v.visitor.phone} • {v.visitor.email}</Text>
                </Stack>
              ),
            },
            {
              key: "purpose",
              header: "Purpose / Zones",
              render: (v: VisitRequest) => (
                <Stack gap={2}>
                  <Text size="sm">{v.purpose}</Text>
                  <Text size="xs" c="dimmed">Zones: {v.access_zones?.join(", ") || "Main Gate"}</Text>
                </Stack>
              ),
            },
            {
              key: "host",
              header: "Host",
              render: (v: VisitRequest) => `Host #${v.host_id}`,
            },
            {
              key: "status",
              header: "Status",
              render: (v: VisitRequest) => (
                <Badge color={STATUS_COLOR[v.status] ?? "gray"}>{v.status}</Badge>
              ),
            },
            {
              key: "pass",
              header: "Pass QR",
              render: (v: VisitRequest) =>
                v.digital_pass ? (
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<FaQrcode />}
                    onClick={() => setViewingPass(v)}
                  >
                    {v.digital_pass.pass_number}
                  </Button>
                ) : (
                  <Text size="xs" c="dimmed">No pass yet</Text>
                ),
            },
          ]}
        />

        {/* Modal: Pre-register Visitor */}
        <Modal
          opened={registering}
          onClose={() => setRegistering(false)}
          title="Pre-register Visitor"
          size="md"
        >
          <Stack gap="sm">
            <TextInput label="Visitor Full Name" required value={name} onChange={(e) => setName(e.target.value)} />
            <TextInput label="Email Address" required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextInput label="Phone Number" required value={phone} onChange={(e) => setPhone(e.target.value)} />
            <Select
              label="ID Document Type"
              data={["AADHAAR", "PAN", "PASSPORT", "VOTER_ID", "DRIVING_LICENSE", "INSTITUTE_ID"]}
              value={docType}
              onChange={(v) => setDocType(v ?? "AADHAAR")}
            />
            <TextInput label="ID Document Number" required value={docNumber} onChange={(e) => setDocNumber(e.target.value)} />
            <TextInput label="Host Staff/Faculty User ID" required value={hostId} onChange={(e) => setHostId(e.target.value)} />
            <TextInput label="Visit Purpose" required value={purpose} onChange={(e) => setPurpose(e.target.value)} />
            <Select
              label="Advance Notice (Hours from now)"
              data={["2", "3", "6", "12", "24"]}
              value={hoursAdvance}
              onChange={(v) => setHoursAdvance(v ?? "3")}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRegistering(false)}>Cancel</Button>
              <Button loading={preRegister.isPending} onClick={handleRegister}>Submit Registration</Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Digital Pass View */}
        <Modal
          opened={!!viewingPass}
          onClose={() => setViewingPass(null)}
          title="Authoritative Digital Pass"
          size="sm"
        >
          {viewingPass?.digital_pass && (
            <Card withBorder padding="md" radius="md">
              <Stack align="center" gap="xs">
                <FaUserCheck size={36} color="var(--mantine-color-blue-6)" />
                <Text fw={700} size="lg">{viewingPass.visitor.name}</Text>
                <Badge color={STATUS_COLOR[viewingPass.status]}>{viewingPass.status}</Badge>
                <Text size="xs" c="dimmed">Pass Number</Text>
                <Code fw={700}>{viewingPass.digital_pass.pass_number}</Code>
                <Text size="xs" c="dimmed" mt="xs">QR Security Token</Text>
                <Code block style={{ wordBreak: "break-all" }}>{viewingPass.digital_pass.qr_token}</Code>
                <Text size="xs" c="dimmed">
                  Valid: {new Date(viewingPass.digital_pass.valid_from).toLocaleDateString()} - {new Date(viewingPass.digital_pass.valid_to).toLocaleDateString()}
                </Text>
              </Stack>
            </Card>
          )}
        </Modal>
      </Stack>
    </Container>
  );
}
