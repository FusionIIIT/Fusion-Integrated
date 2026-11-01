import { Card, Container, Group, Text, Badge } from "@mantine/core";
import { FaCalendarAlt, FaClock, FaMapMarkerAlt, FaUserTie } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useScheduledSeminars } from "../api/hooks";
import type { GraduateSeminar } from "../api/types";

export default function SeminarCalendarPage() {
  const { data, isPending, error } = useScheduledSeminars();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const seminars = data ?? [];

  const columns = [
    {
      key: "date_time",
      header: "Date & Time",
      render: (s: GraduateSeminar) => (
        <div>
          <Group gap="xs">
            <FaCalendarAlt size={12} color="#228be6" />
            <Text fw={600} size="sm">{s.scheduled_date}</Text>
          </Group>
          <Group gap="xs" mt={2}>
            <FaClock size={12} color="#868e96" />
            <Text size="xs" c="dimmed">{s.start_time} - {s.end_time}</Text>
          </Group>
        </div>
      ),
    },
    {
      key: "seminar",
      header: "Title & Speaker",
      render: (s: GraduateSeminar) => (
        <div>
          <Text fw={600} size="sm">{s.title}</Text>
          <Text size="xs" c="dimmed">Speaker: {s.speaker_name}</Text>
        </div>
      ),
    },
    {
      key: "venue",
      header: "Venue",
      render: (s: GraduateSeminar) => (
        <Group gap="xs">
          <FaMapMarkerAlt size={12} color="#e03131" />
          <Badge variant="light" color="blue" size="sm">
            {s.venue}
          </Badge>
        </Group>
      ),
    },
    {
      key: "chair",
      header: "Session Chair",
      render: (s: GraduateSeminar) => (
        <Group gap="xs">
          <FaUserTie size={12} color="#7950f2" />
          <Text size="sm">{s.session_chair || "Department Panel"}</Text>
        </Group>
      ),
    },
    {
      key: "scheduled_by",
      header: "Scheduled By",
      render: (s: GraduateSeminar) => (
        <Text size="xs" c="dimmed">
          {s.scheduled_by_name || `Admin #${s.scheduled_by_id}`}
        </Text>
      ),
    },
  ];

  return (
    <Container size="xl">
      <PageHeader
        title="Graduate Seminar Schedule"
        subtitle="Department scheduled seminars, presentations, and venue allocations (AFR-OAP-049)"
      />

      <Card padding="lg" withBorder>
        <DataTable<GraduateSeminar>
          rows={seminars}
          columns={columns}
          loading={isPending}
          rowKey={(s) => s.id}
          empty={{
            icon: FaCalendarAlt,
            title: "No Seminars Scheduled",
            description: "There are currently no graduate seminars scheduled in the department.",
          }}
        />
      </Card>
    </Container>
  );
}
