import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { FaPlus, FaShieldAlt } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useCreateSecurityShift,
  useHostels,
  useSecurityShifts,
} from "../api/hooks";
import type { SecurityGuardShift } from "../api/types";

export default function SecurityShiftsPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [shiftDate, setShiftDate] = useState<string>(() => new Date().toISOString().slice(0, 10));

  const {
    data: shifts,
    isPending,
    error,
  } = useSecurityShifts({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    shift_date: shiftDate || undefined,
  });

  const createShiftMutation = useCreateSecurityShift();

  // Shift Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [sHostelId, setSHostelId] = useState<string | null>(null);
  const [sGuardName, setSGuardName] = useState("");
  const [sBadge, setSBadge] = useState("");
  const [sShiftType, setSShiftType] = useState<string | null>("morning");
  const [sDate, setSDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [sPost, setSPost] = useState("Main Gate");
  const [sContact, setSContact] = useState("");
  const [sSupervisor, setSSupervisor] = useState("Chief Security Officer");
  const [sVerified, setSVerified] = useState(true);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleSaveShift = async () => {
    if (!sHostelId || !sGuardName || !sDate) return;
    await createShiftMutation.mutateAsync({
      hostel: Number(sHostelId),
      guard_name: sGuardName,
      agency_or_badge_number: sBadge,
      shift_type: sShiftType || "morning",
      shift_date: sDate,
      gate_or_post: sPost,
      contact_number: sContact,
      supervisor_name: sSupervisor,
      is_verified: sVerified,
    });
    setModalOpen(false);
    setSGuardName("");
    setSBadge("");
    setSContact("");
  };

  const getShiftBadge = (type: string) => {
    const colors: Record<string, string> = {
      morning: "orange",
      evening: "blue",
      night: "indigo",
    };
    return <Badge color={colors[type] || "gray"}>{type.toUpperCase()}</Badge>;
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Security Guard Shift Roster"
          subtitle="Plan guard duty allocations, monitor gate posts, and conduct supervisory verification"
          action={
            <Button
              leftSection={<FaPlus />}
              onClick={() => {
                if (hostels && hostels.length > 0 && hostels[0]) setSHostelId(String(hostels[0].id));
                setModalOpen(true);
              }}
            >
              Schedule Guard Shift
            </Button>
          }
        />

        <Card withBorder radius="md">
          <Group justify="space-between" mb="md">
            <Group>
              <Select
                placeholder="Filter by hostel"
                clearable
                value={selectedHostel}
                onChange={setSelectedHostel}
                data={(hostels || []).map((h) => ({
                  value: String(h.id),
                  label: `${h.name} (${h.code})`,
                }))}
                style={{ width: 260 }}
              />

              <TextInput
                type="date"
                label=""
                value={shiftDate}
                onChange={(e) => setShiftDate(e.target.value)}
                style={{ width: 180 }}
              />
            </Group>

            <Badge variant="outline" size="lg" leftSection={<FaShieldAlt />}>
              {shifts?.length || 0} Shift Assignments
            </Badge>
          </Group>

          <DataTable<SecurityGuardShift>
            rows={shifts || []}
            loading={isPending}
            rowKey={(r) => r.id}
            columns={[
              {
                key: "id",
                header: "ID",
                render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
              },
              {
                key: "guard",
                header: "Guard Name & Badge",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm" fw={600}>{r.guard_name}</Text>
                    <Text size="xs" c="dimmed">
                      {r.agency_or_badge_number ? `Badge: ${r.agency_or_badge_number}` : "Agency Staff"}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "hostel",
                header: "Hostel",
                render: (r) => <Text size="sm">{r.hostel_name}</Text>,
              },
              {
                key: "shift",
                header: "Shift",
                render: (r) => getShiftBadge(r.shift_type),
              },
              {
                key: "date",
                header: "Date",
                render: (r) => <Text size="xs">{r.shift_date}</Text>,
              },
              {
                key: "post",
                header: "Post / Gate",
                render: (r) => <Text size="xs" fw={500}>{r.gate_or_post}</Text>,
              },
              {
                key: "supervisor",
                header: "Supervisor & Contact",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="xs">{r.supervisor_name || "Head Guard"}</Text>
                    <Text size="xs" c="dimmed">{r.contact_number || "N/A"}</Text>
                  </Stack>
                ),
              },
              {
                key: "status",
                header: "Verification",
                render: (r) => (
                  <Badge color={r.is_verified ? "teal" : "yellow"} variant="light">
                    {r.is_verified ? "Verified on Post" : "Pending Check"}
                  </Badge>
                ),
              },
            ]}
            empty={{
              title: "No Security Shifts",
              description: "No security shifts scheduled for this date.",
            }}
          />
        </Card>

        {/* Modal: Schedule Shift */}
        <Modal
          opened={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Schedule Security Guard Shift"
          size="md"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={sHostelId}
              onChange={setSHostelId}
            />

            <Group grow>
              <TextInput
                label="Guard Full Name"
                required
                placeholder="e.g. Surendra Singh"
                value={sGuardName}
                onChange={(e) => setSGuardName(e.target.value)}
              />
              <TextInput
                label="Badge / Agency ID"
                placeholder="e.g. SEC-889"
                value={sBadge}
                onChange={(e) => setSBadge(e.target.value)}
              />
            </Group>

            <Group grow>
              <Select
                label="Shift Type"
                required
                data={[
                  { value: "morning", label: "Morning (06:00 - 14:00)" },
                  { value: "evening", label: "Evening (14:00 - 22:00)" },
                  { value: "night", label: "Night (22:00 - 06:00)" },
                ]}
                value={sShiftType}
                onChange={setSShiftType}
              />
              <TextInput
                label="Shift Date"
                type="date"
                required
                value={sDate}
                onChange={(e) => setSDate(e.target.value)}
              />
            </Group>

            <Group grow>
              <TextInput
                label="Gate / Post Location"
                required
                placeholder="e.g. Main Gate, Rear Barrier, Hall A Reception"
                value={sPost}
                onChange={(e) => setSPost(e.target.value)}
              />
              <TextInput
                label="Contact Number"
                placeholder="Guard mobile"
                value={sContact}
                onChange={(e) => setSContact(e.target.value)}
              />
            </Group>

            <TextInput
              label="Supervising Officer"
              placeholder="e.g. Security Officer / Warden"
              value={sSupervisor}
              onChange={(e) => setSSupervisor(e.target.value)}
            />

            <Checkbox
              label="Post attendance verified by supervisor upon reporting"
              checked={sVerified}
              onChange={(e) => setSVerified(e.currentTarget.checked)}
              mt="xs"
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={createShiftMutation.isPending}
                disabled={!sHostelId || !sGuardName || !sDate}
                onClick={handleSaveShift}
              >
                Schedule Shift
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
