import { Card, Container } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useRooms } from "../api/hooks";
import type { Room } from "../api/types";

export default function RoomsPage() {
  const { data, isPending, error } = useRooms();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Rooms"
        subtitle="Current room configurations, capacity, and derived occupancy"
      />
      <Card padding="lg">
        <DataTable<Room>
          rows={data ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "id", header: "ID", render: (r) => `#${r.id}` },
            { key: "room_number", header: "Room Number" },
            { key: "capacity", header: "Total Capacity" },
            { key: "occupied_count", header: "Occupied" },
            { key: "available_capacity", header: "Available" },
            {
              key: "is_active",
              header: "Status",
              render: (r) => <StatusBadge status={r.is_active ? "active" : "inactive"} />,
            },
          ]}
        />
      </Card>
    </Container>
  );
}
