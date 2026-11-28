import { useState } from "react";
import { Badge, Button, Card, Container, Group, Text } from "@mantine/core";
import { FaCalendarAlt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBookings, useMyClubs } from "../api/hooks";
import type { Booking } from "../api/types";
import { BookingModal } from "../components/BookingModal";

/** Sessions and events of the clubs one leads or belongs to; Club Heads book here. */
export default function SchedulePage() {
  const { can } = useAuth();
  const bookings = useBookings();
  const mine = useMyClubs();
  const [booking, setBooking] = useState<"session" | "event" | null>(null);
  const leading = mine.data?.leading ?? [];
  const mayBook = can("gymkhana.booking.create") && leading.length > 0;

  const error = bookings.error ?? mine.error;
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Club Schedule"
        subtitle="Sessions and events of the clubs you lead or belong to"
        action={mayBook ? (
          <Group>
            <Button variant="default" onClick={() => setBooking("session")}>Book session</Button>
            <Button onClick={() => setBooking("event")}>Book event</Button>
          </Group>) : null} />
      <Card padding="lg">
        <DataTable<Booking>
          rows={bookings.data?.results ?? []}
          loading={bookings.isPending}
          rowKey={(b) => b.id}
          empty={{ icon: FaCalendarAlt, title: "Nothing scheduled",
            description: "Bookings show here for clubs you lead or are a confirmed member of." }}
          columns={[
            { key: "date", header: "Date", render: (b) => b.date },
            { key: "time", header: "Time", render: (b) =>
              `${b.start_time.slice(0, 5)} to ${b.end_time.slice(0, 5)}` },
            { key: "what", header: "What", render: (b) => (
              <div><Group gap={6}><Badge variant="light"
                color={b.kind === "event" ? "grape" : "blue"}>{b.kind}</Badge>
                <Text fw={600} size="sm">{b.event_name || b.club_name}</Text></Group>
                <Text size="xs" c="dimmed" lineClamp={2}>{b.description}</Text></div>) },
            { key: "venue", header: "Venue", render: (b) => b.venue_name },
            { key: "poster", header: "Poster", render: (b) => b.poster_link
              ? <a href={b.poster_link} target="_blank" rel="noreferrer noopener">Open</a>
              : <Text size="sm" c="dimmed">None</Text> },
          ]}
        />
      </Card>
      {booking && <BookingModal kind={booking} clubs={leading} opened
        onClose={() => setBooking(null)} />}
    </Container>
  );
}
