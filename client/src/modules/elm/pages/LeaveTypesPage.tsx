import { Button, Card, Container, Group, NumberInput, Select, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes, useCreateLeaveType, useAllotBalance } from "../api";
import type { LeaveType } from "../api";
import { useState } from "react";

export default function LeaveTypesPage() {
  const { data, isPending, error } = useLeaveTypes();
  const create = useCreateLeaveType();
  const allot = useAllotBalance();

  const [code, setCode] = useState<string>("");
  const [name, setName] = useState<string>("");
  const [maxDays, setMaxDays] = useState<number>(0);
  const [employeeId, setEmployeeId] = useState<number>(0);
  const [typeId, setTypeId] = useState<number | null>(null);
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [allotted, setAllotted] = useState<number>(0);

  if (error) {
    return <Container size="xl"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Types & Allotment" subtitle="Configure leave categories and allot balances" />
      <Stack gap="lg">
        <Card padding="lg">
          <DataTable<LeaveType>
            rows={data ?? []}
            loading={isPending}
            rowKey={(r) => r.id}
            columns={[
              { key: "code", header: "Code" },
              { key: "name", header: "Name" },
              { key: "max_days_per_year", header: "Max days/year" },
            ]}
            empty={{ title: "No leave types yet" }}
          />
        </Card>
        <Card padding="lg">
          <Text fw={600}>New leave type</Text>
          <Group>
            <TextInput label="Code" value={code} onChange={(e) => setCode(e.target.value)} />
            <TextInput label="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <NumberInput label="Max days per year" value={maxDays} onChange={(value) => setMaxDays(Number(value) || 0)} />
          </Group>
          <Button
            onClick={() => create.mutate({ code, name, max_days_per_year: maxDays }, {
              onSuccess: () => {
                notifications.show({ color: "green", title: "Saved", message: "Leave type created" });
                setCode("");
                setName("");
                setMaxDays(0);
              },
              onError: (e: unknown) => {
                notifications.show({ color: "red", title: "Error", message: errorMessage(e) });
              },
            })}
            disabled={!code || !name}
          >
            Create
          </Button>
        </Card>
        <Card padding="lg">
          <Text fw={600}>Allot balance</Text>
          <Group>
            <NumberInput label="Employee id" value={employeeId} onChange={(value) => setEmployeeId(Number(value) || 0)} />
            <Select
              label="Leave type"
              value={typeId === null ? null : String(typeId)}
              onChange={(value) => setTypeId(value ? Number(value) : null)}
              data={data ? data.map(t => ({ value: String(t.id), label: `${t.name} (${t.code})` })) : []}
            />
            <NumberInput label="Year" value={year} onChange={(value) => setYear(Number(value) || 0)} />
            <NumberInput label="Allotted days" value={allotted} onChange={(value) => setAllotted(Number(value) || 0)} />
          </Group>
          <Button
            onClick={() => allot.mutate({ employee_id: employeeId, leave_type_id: typeId!, year, allotted }, {
              onSuccess: () => {
                notifications.show({ color: "green", title: "Saved", message: "Balance allotted" });
                setEmployeeId(0);
                setTypeId(null);
                setYear(new Date().getFullYear());
                setAllotted(0);
              },
              onError: (e: unknown) => {
                notifications.show({ color: "red", title: "Error", message: errorMessage(e) });
              },
            })}
            disabled={!employeeId || !typeId}
          >
            Allot
          </Button>
        </Card>
      </Stack>
    </Container>
  );
}
