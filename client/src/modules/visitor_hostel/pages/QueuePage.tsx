import { Alert, Button, Card, Group, Text, Textarea, Title } from "@mantine/core";
import { useState } from "react";

import { useBookings, useReviewBooking } from "../api/hooks";

export default function QueuePage() {
  const { data, isLoading, isError } = useBookings("pending");
  const review = useReviewBooking();
  const [reason, setReason] = useState("");
  if (isLoading) return <Text>Loading queue...</Text>;
  if (isError) return <Alert color="red" title="Could not load the queue">Try again.</Alert>;
  const bookings = Array.isArray(data) ? data : data?.results ?? [];
  return (
    <>
      <Title order={2} mb="md">Booking requests</Title>
      {bookings.length === 0
        ? <Alert title="Queue is clear">There are no pending booking requests.</Alert>
        : bookings.map((booking) => (
          <Card key={booking.id} withBorder mb="sm">
            <Text fw={600}>{booking.visitor_name}</Text>
            <Text size="sm">{booking.arrival_date} to {booking.departure_date}</Text>
            <Textarea label="Decision reason" value={reason}
              onChange={(event) => setReason(event.currentTarget.value)} />
            <Group mt="sm">
              <Button onClick={() => review.mutate({
                id: booking.id, outcome: "forward", reason,
              })}>Forward</Button>
              <Button color="red" onClick={() => review.mutate({
                id: booking.id, outcome: "reject", reason,
              })}>Reject</Button>
            </Group>
          </Card>
        ))}
    </>
  );
}
