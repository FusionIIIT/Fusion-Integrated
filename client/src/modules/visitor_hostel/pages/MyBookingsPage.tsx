import { Alert, Badge, Card, SimpleGrid, Text, Title } from "@mantine/core";

import { useBookings } from "../api/hooks";

export default function MyBookingsPage() {
  const { data, isLoading, isError } = useBookings();
  if (isLoading) return <Text>Loading bookings...</Text>;
  if (isError) return <Alert color="red" title="Could not load bookings">Try again.</Alert>;
  const bookings = Array.isArray(data) ? data : data?.results ?? [];
  return (
    <>
      <Title order={2} mb="md">My bookings</Title>
      {bookings.length === 0
        ? <Alert title="No bookings">No visitor booking requests have been submitted.</Alert>
        : <SimpleGrid cols={{ base: 1, md: 2 }}>
          {bookings.map((booking) => (
            <Card key={booking.id} withBorder>
              <Badge>{booking.status}</Badge>
              <Text fw={600} mt="xs">{booking.visitor_name}</Text>
              <Text size="sm">{booking.arrival_date} to {booking.departure_date}</Text>
              {booking.decision_reason && <Text size="sm" c="red">{booking.decision_reason}</Text>}
            </Card>
          ))}
        </SimpleGrid>}
    </>
  );
}
