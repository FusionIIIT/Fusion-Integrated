import { useState } from "react";
import { Badge, Group, NumberInput, Text } from "@mantine/core";
import { Column, DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHolidayCalendar } from "../api/hooks";
import type { HolidayItem } from "../api/types";

export default function HolidayCalendarPage() {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);
  const { data: holidays = [], isLoading } = useHolidayCalendar(selectedYear);

  const columns: Column<HolidayItem>[] = [
    {
      key: "date",
      header: "Date",
      render: (r) => <Text fw={600}>{r.date}</Text>,
    },
    {
      key: "name",
      header: "Holiday Name",
      render: (r) => <Text size="sm">{r.name}</Text>,
    },
    {
      key: "type",
      header: "Type",
      render: (r) => (
        <Group gap="xs">
          {r.is_restricted_holiday ? (
            <Badge color="orange" variant="light">
              Restricted Holiday (RH)
            </Badge>
          ) : (
            <Badge color="blue" variant="light">
              Closed Holiday
            </Badge>
          )}
        </Group>
      ),
    },
    {
      key: "published",
      header: "Status",
      render: (r) => (
        <Badge color={r.is_published ? "green" : "gray"} size="xs">
          {r.is_published ? "Published & Effective" : "Draft"}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Published Holiday & RH Calendar"
        subtitle="Effective calendar governing leave-day counting and Restricted Holiday (RH) validation"
        action={
          <Group gap="xs">
            <Text size="sm">Year:</Text>
            <NumberInput
              w={100}
              value={selectedYear}
              onChange={(val) => setSelectedYear(Number(val) || currentYear)}
              min={2020}
              max={2035}
            />
          </Group>
        }
      />

      <DataTable
        rows={holidays}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No published holidays found",
          description: "No published holiday calendar available for this year.",
        }}
      />
    </div>
  );
}
