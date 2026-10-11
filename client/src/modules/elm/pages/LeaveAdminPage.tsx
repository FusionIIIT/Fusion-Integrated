import { useState } from "react";
import {
  Button, Card, Checkbox, Container, Group, NumberInput, SimpleGrid, Stack,
  Table, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateHoliday, useCreateLeaveType, useDeleteHoliday, useHolidays,
  useLeaveTypes, useSetLeaveTypeActive,
} from "../api/hooks";

export default function LeaveAdminPage() {
  const types = useLeaveTypes();
  const holidays = useHolidays();
  const createType = useCreateLeaveType();
  const setActive = useSetLeaveTypeActive();
  const createHoliday = useCreateHoliday();
  const deleteHoliday = useDeleteHoliday();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [entitlement, setEntitlement] = useState(0);
  const [halfDay, setHalfDay] = useState(false);
  const [reasonRequired, setReasonRequired] = useState(false);
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayName, setHolidayName] = useState("");

  const firstError = types.error ?? holidays.error;
  if (firstError) {
    return <Container size="xl"><ErrorState error={firstError} /></Container>;
  }

  function onCreateType() {
    createType.mutate(
      {
        code, name, annual_entitlement_days: String(entitlement),
        allows_half_day: halfDay, requires_reason: reasonRequired,
        effective_from: effectiveFrom || null,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Leave type version created",
            message: `${code.toUpperCase()} is effective from `
              + `${effectiveFrom || "today"}.`,
          });
          setCode(""); setName(""); setEntitlement(0); setEffectiveFrom("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not create the type", message: errorMessage(e),
        }),
      },
    );
  }

  function onAddHoliday() {
    createHoliday.mutate(
      { date: holidayDate, name: holidayName },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Holiday added", message: holidayDate,
          });
          setHolidayDate(""); setHolidayName("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not add the holiday", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Setup"
        subtitle="Types are effective-dated: a change is a new version, never an edit"
      />
      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
        <Card padding="lg">
          <Text fw={600} mb="sm">Leave type versions</Text>
          <Table striped withTableBorder mb="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Code</Table.Th>
                <Table.Th>Effective from</Table.Th>
                <Table.Th>Entitlement</Table.Th>
                <Table.Th>State</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(types.data ?? []).map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>{t.code} — {t.name}</Table.Td>
                  <Table.Td>{t.effective_from}</Table.Td>
                  <Table.Td>{t.annual_entitlement_days}</Table.Td>
                  <Table.Td>{t.is_active ? "Active" : "Retired"}</Table.Td>
                  <Table.Td>
                    <Button
                      size="xs" variant="subtle"
                      onClick={() => setActive.mutate({
                        id: t.id, action: t.is_active ? "deactivate" : "activate",
                      })}
                    >
                      {t.is_active ? "Retire" : "Restore"}
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Stack>
            <Group grow>
              <TextInput label="Code" value={code} placeholder="CL"
                         onChange={(e) => setCode(e.currentTarget.value)} />
              <TextInput label="Name" value={name} placeholder="Casual Leave"
                         onChange={(e) => setName(e.currentTarget.value)} />
            </Group>
            <Group grow>
              <NumberInput label="Annual entitlement (days)" value={entitlement}
                           min={0} onChange={(v) => setEntitlement(Number(v) || 0)} />
              <TextInput label="Effective from" type="date" value={effectiveFrom}
                         onChange={(e) => setEffectiveFrom(e.currentTarget.value)} />
            </Group>
            <Group>
              <Checkbox label="Half days allowed" checked={halfDay}
                        onChange={(e) => setHalfDay(e.currentTarget.checked)} />
              <Checkbox label="Reason required" checked={reasonRequired}
                        onChange={(e) => setReasonRequired(e.currentTarget.checked)} />
            </Group>
            <Group justify="flex-end">
              <Button loading={createType.isPending} disabled={!code || !name}
                      onClick={onCreateType}>
                Create version
              </Button>
            </Group>
          </Stack>
        </Card>

        <Card padding="lg">
          <Text fw={600} mb="sm">Holiday calendar</Text>
          <Table striped withTableBorder mb="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th>Name</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(holidays.data ?? []).map((h) => (
                <Table.Tr key={h.id}>
                  <Table.Td>{h.date}</Table.Td>
                  <Table.Td>{h.name}</Table.Td>
                  <Table.Td>
                    <Button size="xs" variant="subtle" color="red"
                            onClick={() => deleteHoliday.mutate(h.id)}>
                      Remove
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Stack>
            <Group grow>
              <TextInput label="Date" type="date" value={holidayDate}
                         onChange={(e) => setHolidayDate(e.currentTarget.value)} />
              <TextInput label="Name" value={holidayName}
                         placeholder="Founder's Day"
                         onChange={(e) => setHolidayName(e.currentTarget.value)} />
            </Group>
            <Group justify="flex-end">
              <Button loading={createHoliday.isPending}
                      disabled={!holidayDate || !holidayName}
                      onClick={onAddHoliday}>
                Add holiday
              </Button>
            </Group>
          </Stack>
        </Card>
      </SimpleGrid>
    </Container>
  );
}
