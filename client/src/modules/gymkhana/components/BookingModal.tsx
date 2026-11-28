import { useState } from "react";
import { Select, SimpleGrid, Textarea, TextInput } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { useBook, useVenues } from "../api/hooks";
import type { Club } from "../api/types";
import { notifyDone } from "./notify";

const BLANK = { club: "", venue: "", date: "", start: "", end: "", description: "",
  poster: "", eventName: "" };

/** UC-GYM-002 and UC-GYM-003: the server checks the venue, the times and every overlap. */
export function BookingModal({ kind, clubs, opened, onClose }: {
  kind: "session" | "event";
  clubs: Club[];
  opened: boolean;
  onClose: () => void;
}) {
  const book = useBook(kind);
  const venues = useVenues(opened);
  const [f, setF] = useState(BLANK);
  const set = (k: keyof typeof BLANK) => (v: string) => setF((s) => ({ ...s, [k]: v }));
  const isEvent = kind === "event";
  const missing = !f.club || !f.venue || !f.date || !f.start || !f.end || !f.description.trim()
    || (isEvent && (!f.eventName.trim() || !f.poster.trim()));

  function close() {
    setF(BLANK);
    book.reset();
    onClose();
  }

  function submit() {
    book.mutate({ club_id: Number(f.club), venue: f.venue, date: f.date, start_time: f.start,
      end_time: f.end, description: f.description, poster_url: f.poster,
      ...(isEvent ? { event_name: f.eventName } : {}) }, {
      onSuccess: (b) => {
        notifyDone("Booked", `${b.venue_name} on ${b.date}, ${b.start_time.slice(0, 5)} to `
          + `${b.end_time.slice(0, 5)}. Members are being notified.`);
        close();
      },
    });
  }

  return (
    <FormModal opened={opened} onClose={close} onSubmit={submit}
      title={isEvent ? "Book an event" : "Book a session"}
      subtitle="No session or event may overlap another in the same venue"
      submitLabel="Book" submitting={book.isPending} error={book.error ?? venues.error}
      disabled={missing} disabledReason="Fill in every required field.">
      <Select label="Club" required value={f.club} onChange={(v) => set("club")(v ?? "")}
        data={clubs.map((c) => ({ value: String(c.id), label: c.name }))} />
      {isEvent && <TextInput mt="sm" label="Event name" required maxLength={200}
        value={f.eventName} onChange={(e) => set("eventName")(e.currentTarget.value)} />}
      <Select mt="sm" label="Venue" required value={f.venue}
        onChange={(v) => set("venue")(v ?? "")} data={venues.data?.venues ?? []}
        nothingFoundMessage="No venues are configured" />
      <SimpleGrid cols={3} mt="sm">
        <TextInput type="date" label="Date" required value={f.date}
          onChange={(e) => set("date")(e.currentTarget.value)} />
        <TextInput type="time" label="Start time" required value={f.start}
          onChange={(e) => set("start")(e.currentTarget.value)} />
        <TextInput type="time" label="End time" required value={f.end}
          onChange={(e) => set("end")(e.currentTarget.value)} />
      </SimpleGrid>
      <Textarea mt="sm" label="Description" required autosize minRows={3} maxLength={4000}
        value={f.description} onChange={(e) => set("description")(e.currentTarget.value)} />
      <TextInput mt="sm" label={isEvent ? "Poster (Google Drive link)"
        : "Poster (Google Drive link, optional)"} required={isEvent} value={f.poster}
        onChange={(e) => set("poster")(e.currentTarget.value)} />
    </FormModal>
  );
}
