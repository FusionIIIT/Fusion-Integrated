import { Badge, Button, Card, Container, Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { FaCalendarAlt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSchedule } from "../api/hooks";
import type { DoctorSchedule } from "../api/types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function SchedulePage() {
  const { data, isPending, error } = useSchedule();
  const { can } = useAuth();
  const navigate = useNavigate();
  const canManage = can("phc.schedule.manage");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Doctor Schedule"
        subtitle="Published weekly slots and today's availability"
        action={canManage && (
          <Button
            variant="default" size="xs" onClick={() => navigate("/phc/staff/schedule")}
          >
            Manage schedule
          </Button>
        )}
      />

      <Card padding="lg">
        <DataTable<DoctorSchedule>
          rows={data?.schedules ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={760}
          columns={[
            {
              key: "doctor_name", header: "Doctor",
              render: (r) => <Text fw={600}>{r.doctor_name}</Text>,
            },
            { key: "day_of_week", header: "Day",
              render: (r) => DAYS[r.day_of_week] ?? "—" },
            { key: "time", header: "Time",
              render: (r) => `${r.start_time} – ${r.end_time}` },
            {
              key: "today", header: "Today",
              render: (r) => {
                const status = data?.attendance?.[r.doctor_name];
                return status ? (
                  <Badge
                    color={status === "available" ? "green" : "gray"}
                    variant="light" size="sm"
                  >
                    {status}
                  </Badge>
                ) : <Text size="sm" c="dimmed">Not marked</Text>;
              },
            },
            {
              key: "published_at", header: "Published",
              render: (r) => r.published_at
                ? new Date(r.published_at).toLocaleDateString() : "—",
            },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No published schedule yet",
            description: "Published doctor slots will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
