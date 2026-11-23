import { Badge, Button, Stack, Text } from "@mantine/core";
import { FaCalendarAlt } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { useDownload } from "../api/hooks";
import type { Booking } from "../api/types";
import { date, time } from "./format";
import { refused } from "./toasts";

export function BookingTable({ rows, loading }: { rows: Booking[]; loading: boolean }) {
  const download = useDownload();
  return (
    <DataTable<Booking>
      rows={rows} loading={loading} rowKey={(b) => b.id}
      columns={[
        {
          key: "name", header: "What",
          render: (b) => (
            <Stack gap={0}>
              <Text fw={600}>{b.name}</Text>
              <Text size="xs" c="dimmed">{b.club_name}</Text>
            </Stack>
          ),
        },
        {
          key: "booking_type", header: "Type",
          render: (b) => (
            <Badge variant="light" color={b.booking_type === "event" ? "violet" : "blue"}>
              {b.booking_type}
            </Badge>
          ),
        },
        { key: "venue", header: "Venue" },
        { key: "booking_date", header: "Date", render: (b) => date(b.booking_date) },
        {
          key: "time", header: "Time",
          render: (b) => `${time(b.start_time)} – ${time(b.end_time)}`,
        },
        {
          key: "poster", header: "", align: "right",
          render: (b) => b.poster_file && (
            <Button
              size="xs" variant="light" aria-label={`Download poster for ${b.name}`}
              onClick={() => download.mutate(b.poster_file ?? "", {
                onError: (e) => refused("Could not download the poster", e),
              })}
            >
              Poster
            </Button>
          ),
        },
      ]}
      empty={{
        icon: FaCalendarAlt, title: "No bookings",
        description: "Booked sessions and events appear here.",
      }}
    />
  );
}
