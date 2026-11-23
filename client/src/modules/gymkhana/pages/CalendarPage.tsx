import { useState } from "react";
import { Card, Container, Group, Select, TextInput } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useBookings, useVenues } from "../api/hooks";
import { BookingTable } from "../components/BookingTable";
import { LoadMore } from "../components/LoadMore";
import { PageError } from "../components/PageError";

export default function CalendarPage() {
  const [venue, setVenue] = useState<string | null>(null);
  const [day, setDay] = useState("");
  const venues = useVenues();
  const bookings = useBookings({ venue: venue ?? undefined, booking_date: day || undefined });
  const error = bookings.error ?? venues.error;
  if (error) return <PageError error={error} />;

  return (
    <Container size="xl">
      <PageHeader title="Events & Sessions" subtitle="What clubs have booked, and where" />
      <Card padding="lg">
        <Group mb="md" align="flex-end">
          <Select label="Venue" placeholder="All venues" clearable
            data={venues.data ?? []} value={venue} onChange={setVenue} />
          <TextInput label="Date" type="date" value={day}
            onChange={(e) => setDay(e.currentTarget.value)} />
        </Group>
        <BookingTable rows={bookings.rows} loading={bookings.loading} />
        <LoadMore list={bookings} />
      </Card>
    </Container>
  );
}
