import { useState } from "react";
import {
  Badge, Button, Card, Checkbox, Container, Group, NumberInput, Select, SimpleGrid,
  Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useApply, useBalances, useCancel, useRequests, useWithdraw,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";

const CATEGORIES = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

export const STATUS_COLOR: Record<string, string> = {
  substitute_pending: "yellow", unit_review: "blue", routing: "indigo",
  sanction: "violet", approved: "green", rejected: "red", withdrawn: "gray",
  cancelled: "gray",
};

const PENDING = new Set(["substitute_pending", "unit_review", "routing", "sanction"]);

/** An employee's balances, own requests and new applications (EL-UC-001/007/008/012). */
export default function MyLeavePage() {
  const { can, session } = useAuth();
  const requests = useRequests();
  const balances = useBalances();
  const withdraw = useWithdraw();
  const cancel = useCancel();
  const [applying, setApplying] = useState(false);

  const error = requests.error || balances.error;
  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const mine = (requests.data?.results ?? []).filter((r) => r.user_id === session?.user.id);
  const onError = (title: string) => (e: unknown) =>
    notifications.show({ color: "red", title, message: errorMessage(e) });

  return (
    <Container size="md">
      <PageHeader
        title="My leave"
        subtitle="Balances for this year and every leave request you have made"
        action={can("leave.request.create") && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setApplying(true)}>
            Apply for leave
          </Button>
        )}
      />

      <SimpleGrid cols={{ base: 2, sm: 3 }} mb="lg">
        {(balances.data ?? []).map((b) => (
          <Card key={b.id} withBorder padding="md">
            <Text size="xs" c="dimmed">{b.category}</Text>
            <Text fw={700} size="lg">{b.available}</Text>
            <Text size="xs" c="dimmed">of {b.entitled} available</Text>
          </Card>
        ))}
      </SimpleGrid>

      {requests.isPending && <Text c="dimmed">Loading…</Text>}

      {!requests.isPending && mine.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaCalendarAlt size={24} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>You have not applied for leave yet</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {mine.map((r: LeaveRequest) => (
          <Card key={r.id} withBorder padding="lg">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700}>{r.category}</Text>
                  <Badge color={STATUS_COLOR[r.status] ?? "gray"} variant="light">
                    {r.status.replace("_", " ")}
                  </Badge>
                  {r.station_leave && <Badge variant="outline" size="sm">station leave</Badge>}
                </Group>
                <Text size="sm">{r.start_date} → {r.end_date} · {r.days} day(s)</Text>
                <Text size="sm" c="dimmed">{r.purpose}</Text>
                {r.decision_note && <Text size="xs">Note: {r.decision_note}</Text>}
              </Stack>
              {PENDING.has(r.status) && (
                <Button size="xs" variant="subtle" color="red" loading={withdraw.isPending}
                  onClick={() => withdraw.mutate(r.id, { onError: onError("Could not withdraw") })}>
                  Withdraw
                </Button>
              )}
              {r.status === "approved" && (
                <Button size="xs" variant="subtle" color="red" loading={cancel.isPending}
                  onClick={() => cancel.mutate(r.id, { onError: onError("Could not cancel") })}>
                  Cancel
                </Button>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      <ApplyModal opened={applying} onClose={() => setApplying(false)} />
    </Container>
  );
}

function ApplyModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const apply = useApply();
  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [purpose, setPurpose] = useState("");
  const [substitute, setSubstitute] = useState<string | number>("");
  const [station, setStation] = useState(false);
  const [address, setAddress] = useState("");

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Apply for leave"
      subtitle="Balance, overlap and category rules are checked when you submit"
      onSubmit={() => apply.mutate(
        {
          category, start_date: start, end_date: end, purpose,
          substitute_user_id: substitute === "" ? null : Number(substitute),
          station_leave: station, station_address: station ? address : "",
        },
        {
          onSuccess: () => {
            notifications.show({ color: "green", title: "Applied", message: "Your request was submitted." });
            setPurpose(""); setStart(""); setEnd(""); setSubstitute(""); onClose();
          },
        },
      )}
      submitLabel="Submit" submitting={apply.isPending} error={apply.error}
      disabled={!category || !start || !end || !purpose.trim() || (station && !address.trim())}
    >
      <Stack gap="md">
        <Select label="Category" data={CATEGORIES} value={category} onChange={setCategory} required />
        <Group grow>
          <TextInput label="From" type="date" required value={start}
            onChange={(e) => setStart(e.currentTarget.value)} />
          <TextInput label="To" type="date" required value={end}
            onChange={(e) => setEnd(e.currentTarget.value)} />
        </Group>
        <Textarea label="Purpose" required autosize minRows={2} value={purpose}
          onChange={(e) => setPurpose(e.currentTarget.value)} />
        <NumberInput label="Substitute (employee id)" description="Optional" min={1}
          value={substitute} onChange={setSubstitute} />
        <Checkbox label="I will be away from Jabalpur (Station Leave)" checked={station}
          onChange={(e) => setStation(e.currentTarget.checked)} />
        {station && (
          <TextInput label="Address while away" required maxLength={200} value={address}
            onChange={(e) => setAddress(e.currentTarget.value)} />
        )}
      </Stack>
    </FormModal>
  );
}
