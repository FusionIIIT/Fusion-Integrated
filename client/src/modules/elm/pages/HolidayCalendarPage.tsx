import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Select,
  Text,
} from "@mantine/core";


import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHolidayCalendar } from "../api/hooks";
import type { HolidayCalendar } from "../api/types";

export default function HolidayCalendarPage() {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState<string>(String(currentYear));

  const { data, isPending, error } = useHolidayCalendar(Number(selectedYear));

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const holidays = (data?.results ?? []) as HolidayCalendar[];

  return (
    <Container size="xl">
      <PageHeader
        title="Holiday Calendar"
        subtitle={`Official Institute published holidays and restricted holidays (RH) for ${selectedYear}`}
        action={
          <Select
            data={[
              { value: String(currentYear - 1), label: String(currentYear - 1) },
              { value: String(currentYear), label: String(currentYear) },
              { value: String(currentYear + 1), label: String(currentYear + 1) },
            ]}
            value={selectedYear}
            onChange={(val) => setSelectedYear(val || String(currentYear))}
            w={120}
          />
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<HolidayCalendar>
          rows={holidays}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={700}
          empty={{
            title: "No published holidays",
            description: "No holidays scheduled for this calendar year",
          }}
          columns={[

            {
              key: "date",
              header: "Date",
              render: (r) => (
                <Text fw={600} size="sm">
                  {new Date(r.date).toLocaleDateString(undefined, {
                    weekday: "short",
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </Text>
              ),
            },
            {
              key: "name",
              header: "Occasion / Holiday",
              render: (r) => (
                <Text size="sm" fw={500}>
                  {r.name}
                </Text>
              ),
            },
            {
              key: "holiday_type",
              header: "Type",
              render: (r) => (
                <Badge
                  color={r.holiday_type === "closed" ? "red" : "violet"}
                  variant="light"
                >
                  {r.holiday_type === "closed" ? "Closed Holiday" : "Restricted Holiday (RH)"}
                </Badge>
              ),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
