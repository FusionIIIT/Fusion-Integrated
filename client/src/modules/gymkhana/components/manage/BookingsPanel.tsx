import { useState } from "react";
import { Button, FileInput, Group, Select, Stack, Textarea, TextInput } from "@mantine/core";

import { ErrorState } from "../../../../ui/components/ErrorState";
import { FormModal } from "../../../../ui/components/FormModal";
import { useBook, useBookings, useVenues } from "../../api/hooks";
import type { LedClub } from "../../api/types";
import { BookingTable } from "../BookingTable";
import { LoadMore } from "../LoadMore";
import { PersonPicker } from "../PersonPicker";
import { done } from "../toasts";

type Kind = "session" | "event";

export function BookingsPanel({ club }: { club: LedClub }) {
  const list = useBookings({ club_id: club.id });
  const [booking, setBooking] = useState<Kind | null>(null);
  if (list.error) return <ErrorState error={list.error} />;
  return (
    <>
      <Group mb="md">
        <Button onClick={() => setBooking("session")}>Book session</Button>
        <Button variant="light" onClick={() => setBooking("event")}>Book event</Button>
      </Group>
      <BookingTable rows={list.rows} loading={list.loading} />
      <LoadMore list={list} />
      {booking && <BookModal kind={booking} club={club} onClose={() => setBooking(null)} />}
    </>
  );
}

function BookModal({ kind, club, onClose }: {
  kind: Kind; club: LedClub; onClose: () => void;
}) {
  const book = useBook();
  const venues = useVenues();
  const [f, setF] = useState({
    name: "", booking_date: "", start_time: "", end_time: "", description: "",
  });
  const [venue, setVenue] = useState<string | null>(null);
  const [faculty, setFaculty] = useState<number | null>(null);
  const [poster, setPoster] = useState<File | null>(null);
  const isEvent = kind === "event";

  const missing = !venue || !f.booking_date || !f.start_time || !f.end_time
    || (isEvent && (!f.name.trim() || faculty === null));
  const backwards = Boolean(f.start_time && f.end_time && f.start_time >= f.end_time);

  return (
    <FormModal
      opened onClose={onClose} title={isEvent ? "Book event" : "Book session"}
      subtitle={club.name} submitLabel="Book" submitting={book.isPending}
      error={book.error ?? venues.error} disabled={missing || backwards}
      disabledReason={backwards ? "The start time must be before the end time."
        : "Fill in every required field."}
      onSubmit={() => venue && book.mutate({
        kind, club_id: club.id, venue, ...f, faculty_councillor_id: faculty, poster_file: poster,
      }, {
        onSuccess: (b) => {
          done("Booked", `${b.name} is booked at ${b.venue}.`);
          onClose();
        },
      })}
    >
      <Stack gap="md">
        <TextInput label={isEvent ? "Event name" : "Session title"} required={isEvent}
          maxLength={150} value={f.name}
          onChange={(e) => setF({ ...f, name: e.currentTarget.value })} />
        {isEvent && (
          <PersonPicker label="Faculty Councillor" kind="faculty" value={faculty}
            onChange={setFaculty} />
        )}
        <Select label="Venue" required data={venues.data ?? []} value={venue}
          onChange={setVenue} />
        <Group grow>
          <TextInput label="Date" type="date" required value={f.booking_date}
            onChange={(e) => setF({ ...f, booking_date: e.currentTarget.value })} />
          <TextInput label="Start time" type="time" required value={f.start_time}
            onChange={(e) => setF({ ...f, start_time: e.currentTarget.value })} />
          <TextInput label="End time" type="time" required value={f.end_time}
            onChange={(e) => setF({ ...f, end_time: e.currentTarget.value })} />
        </Group>
        <Textarea label="Description" autosize minRows={2} value={f.description}
          onChange={(e) => setF({ ...f, description: e.currentTarget.value })} />
        <FileInput label="Poster" placeholder="PDF, JPG or PNG, up to 5 MB" clearable
          accept=".pdf,.jpg,.jpeg,.png" value={poster} onChange={setPoster}
          clearButtonProps={{ "aria-label": "Remove poster" }} />
      </Stack>
    </FormModal>
  );
}
