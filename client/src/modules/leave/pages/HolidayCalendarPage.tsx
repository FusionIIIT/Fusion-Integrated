import { Badge, Card, Container } from "@mantine/core";
import { FaCalendarAlt } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHolidays } from "../api/hooks";
import type { Holiday } from "../api/types";

/** The published holiday/RH calendar RH validation and day counting read. */
export default function HolidayCalendarPage() {
  const { data, isPending, error } = useHolidays();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="lg">
      <PageHeader
        title="Holiday Calendar"
        subtitle="Restricted Holidays an RH request must match, and the closed holidays that count inside EL/COL/VL"
      />
      <Card padding="lg">
        <DataTable<Holiday>
          rows={data ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "on_date", header: "Date" },
            { key: "name", header: "Occasion" },
            { key: "year", header: "Leave year" },
            { key: "kind", header: "Kind",
              render: (r) => (
                <Badge variant="light"
                       color={r.is_closed_holiday ? "gray" : "indigo"}>
                  {r.is_closed_holiday ? "Closed holiday" : "Restricted"}
                </Badge>
              ) },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No calendar published",
            description: "Publish the holiday/RH calendar for this leave year.",
          }}
        />
      </Card>
    </Container>
  );
}
