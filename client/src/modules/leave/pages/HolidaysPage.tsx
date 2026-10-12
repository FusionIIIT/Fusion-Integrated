import { useState } from "react";
import {
  Badge, Button, Card, Checkbox, Container, Stack, Table, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAddHoliday, useHolidays } from "../api/hooks";

/** The published holiday and Restricted Holiday calendar (EL-UC-015, BR-EL-031). */
export default function HolidaysPage() {
  const { data, isPending, error } = useHolidays();
  const { can } = useAuth();
  const [adding, setAdding] = useState(false);

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;
  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader
        title="Holiday calendar"
        subtitle="Closed holidays and Restricted Holidays (RH) used when counting leave days"
        action={can("leave.calendar.manage") && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setAdding(true)}>
            Add holiday
          </Button>
        )}
      />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaCalendarAlt size={24} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No holidays published yet</Text>
          </Stack>
        </Card>
      )}

      {rows.length > 0 && (
        <Card withBorder padding={0}>
          <Table striped>
            <Table.Thead>
              <Table.Tr><Table.Th>Date</Table.Th><Table.Th>Name</Table.Th><Table.Th>Type</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((h) => (
                <Table.Tr key={h.id}>
                  <Table.Td>{h.date}</Table.Td>
                  <Table.Td>{h.name}</Table.Td>
                  <Table.Td>
                    {h.is_restricted
                      ? <Badge color="violet" variant="light">RH</Badge>
                      : <Badge variant="light">Holiday</Badge>}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <AddHolidayModal opened={adding} onClose={() => setAdding(false)} />
    </Container>
  );
}

function AddHolidayModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const addHoliday = useAddHoliday();
  const [date, setDate] = useState("");
  const [name, setName] = useState("");
  const [restricted, setRestricted] = useState(false);

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Add a holiday"
      subtitle="Published holidays immediately affect how CL, RH and SCL days are counted"
      onSubmit={() => addHoliday.mutate(
        { date, name: name.trim(), is_restricted: restricted, is_published: true },
        {
          onSuccess: () => { setDate(""); setName(""); setRestricted(false); onClose(); },
          onError: (e) => notifications.show({
            color: "red", title: "Could not add holiday", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Add" submitting={addHoliday.isPending} error={addHoliday.error}
      disabled={!date || !name.trim()}
    >
      <Stack gap="md">
        <TextInput label="Date" type="date" required value={date}
          onChange={(e) => setDate(e.currentTarget.value)} />
        <TextInput label="Name" required maxLength={120} value={name}
          onChange={(e) => setName(e.currentTarget.value)} />
        <Checkbox label="Restricted Holiday (RH)" checked={restricted}
          onChange={(e) => setRestricted(e.currentTarget.checked)} />
      </Stack>
    </FormModal>
  );
}
