import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useFines,
  useHostels,
  useRecordFine,
} from "../api/hooks";
import type { HostelFine } from "../api/types";

export default function FineManagementPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>("all");

  const {
    data: fines,
    isPending,
    error,
  } = useFines({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
  });

  const recordFineMutation = useRecordFine();

  // Impose fine modal
  const [imposeModalOpen, setImposeModalOpen] = useState(false);
  const [fHostelId, setFHostelId] = useState<string | null>(null);
  const [fStudentUserId, setFStudentUserId] = useState<number | string>(1);
  const [fRollNumber, setFRollNumber] = useState("");
  const [fStudentName, setFStudentName] = useState("");
  const [fType, setFType] = useState<string | null>("damage");
  const [fAmount, setFAmount] = useState<number | string>(500);
  const [fDate, setFDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [fReason, setFReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleImpose = async () => {
    if (!fHostelId || !fRollNumber || !fAmount || !fReason || !fDate) return;
    await recordFineMutation.mutateAsync({
      hostel: Number(fHostelId),
      student_user_id: Number(fStudentUserId) || 1,
      student_roll_number: fRollNumber,
      student_name: fStudentName || fRollNumber,
      fine_type: fType || "rule_violation",
      amount: Number(fAmount),
      date: fDate,
      reason: fReason,
      is_paid: false,
    });
    setImposeModalOpen(false);
    setFRollNumber("");
    setFStudentName("");
    setFReason("");
  };

  const filteredFines = (fines || []).filter((f) => {
    if (activeTab === "unpaid") return !f.is_paid;
    if (activeTab === "paid") return f.is_paid;
    return true;
  });

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Fine & Disciplinary Management"
          subtitle="Enforce student hostel conduct, penalize property damage or violations, and track payment dues"
          action={
            <Button
              leftSection={<FaPlus />}
              onClick={() => {
                if (hostels && hostels.length > 0 && hostels[0]) {
                  setFHostelId(String(hostels[0].id));
                }
                setImposeModalOpen(true);
              }}
            >
              Impose Fine
            </Button>
          }
        />

        <Card withBorder radius="md">
          <Group justify="space-between" mb="md">
            <Select
              placeholder="Filter by hostel"
              clearable
              value={selectedHostel}
              onChange={setSelectedHostel}
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              style={{ width: 280 }}
            />

            <Tabs value={activeTab} onChange={setActiveTab}>
              <Tabs.List>
                <Tabs.Tab value="all">All Fines</Tabs.Tab>
                <Tabs.Tab value="unpaid">Outstanding</Tabs.Tab>
                <Tabs.Tab value="paid">Settled / Paid</Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>

          <DataTable<HostelFine>
            rows={filteredFines}
            loading={isPending}
            rowKey={(r) => r.id}
            columns={[
              {
                key: "id",
                header: "Fine ID",
                render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
              },
              {
                key: "hostel",
                header: "Hostel",
                render: (r) => <Text size="sm" fw={500}>{r.hostel_name}</Text>,
              },
              {
                key: "student",
                header: "Student",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm">{r.student_name || "Student"}</Text>
                    <Text size="xs" c="dimmed">{r.student_roll_number}</Text>
                  </Stack>
                ),
              },
              {
                key: "type",
                header: "Violation Category",
                render: (r) => (
                  <Badge variant="outline" size="sm">
                    {r.fine_type.replace("_", " ").toUpperCase()}
                  </Badge>
                ),
              },
              {
                key: "reason",
                header: "Reason & Violation Details",
                render: (r) => (
                  <Text size="xs" c="dimmed" lineClamp={2}>
                    {r.reason}
                  </Text>
                ),
              },
              {
                key: "amount",
                header: "Amount (₹)",
                render: (r) => (
                  <Text size="sm" fw={700} c={r.is_paid ? "dimmed" : "red"}>
                    ₹{Number(r.amount).toLocaleString()}
                  </Text>
                ),
              },
              {
                key: "date",
                header: "Date Imposed",
                render: (r) => <Text size="xs">{r.date}</Text>,
              },
              {
                key: "status",
                header: "Payment Status",
                render: (r) =>
                  r.is_paid ? (
                    <Badge color="teal" variant="filled">Paid</Badge>
                  ) : (
                    <Badge color="red" variant="light">Outstanding</Badge>
                  ),
              },
            ]}
            empty={{
              title: "No Fines Found",
              description: "No fine or disciplinary records match this selection.",
            }}
          />
        </Card>

        {/* Modal: Impose Fine */}
        <Modal
          opened={imposeModalOpen}
          onClose={() => setImposeModalOpen(false)}
          title="Impose Disciplinary Fine (BR-HM-025)"
          size="lg"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={fHostelId}
              onChange={setFHostelId}
            />

            <Group grow>
              <TextInput
                label="Student Roll Number"
                required
                placeholder="e.g. 21BCS045"
                value={fRollNumber}
                onChange={(e) => setFRollNumber(e.target.value)}
              />
              <TextInput
                label="Student Full Name"
                placeholder="e.g. Rahul Sharma"
                value={fStudentName}
                onChange={(e) => setFStudentName(e.target.value)}
              />
              <NumberInput
                label="Student User ID"
                placeholder="User ID (default 1)"
                min={1}
                value={fStudentUserId}
                onChange={setFStudentUserId}
              />
            </Group>

            <Group grow>
              <Select
                label="Violation Type"
                required
                data={[
                  { value: "damage", label: "Property / Furniture Damage" },
                  { value: "rule_violation", label: "Hostel Rules Violation" },
                  { value: "indiscipline", label: "Indiscipline / Misconduct" },
                  { value: "noise", label: "Noise / Disturbance in Quiet Hours" },
                  { value: "cleanliness", label: "Room / Common Area Mess" },
                  { value: "other", label: "Other Offense" },
                ]}
                value={fType}
                onChange={setFType}
              />
              <NumberInput
                label="Fine Amount (₹)"
                required
                min={1}
                value={fAmount}
                onChange={setFAmount}
              />
              <TextInput
                label="Incident / Imposition Date"
                type="date"
                required
                value={fDate}
                onChange={(e) => setFDate(e.target.value)}
              />
            </Group>

            <Textarea
              label="Mandatory Reason & Incident Summary (BR-HM-025)"
              required
              minRows={3}
              placeholder="State the exact incident, witness remarks, item damaged, or rule violated..."
              value={fReason}
              onChange={(e) => setFReason(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setImposeModalOpen(false)}>
                Cancel
              </Button>
              <Button
                color="red"
                loading={recordFineMutation.isPending}
                disabled={!fHostelId || !fRollNumber || !fAmount || !fReason || !fDate}
                onClick={handleImpose}
              >
                Impose Fine
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
