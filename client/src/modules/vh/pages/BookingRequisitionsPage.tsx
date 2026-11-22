import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInbox, FaShare, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useBookings } from "../api/hooks";
import type { Booking } from "../api/types";

export default function BookingRequisitionsPage() {
  const { data: bookings, isPending, error } = useBookings();
  const [rejectingBooking, setRejectingBooking] = useState<Booking | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const pendingBookings = (bookings ?? []).filter(
    (b) => b.status === "pending" || b.status === "pending_offline"
  );

  const handleForward = async (b: Booking) => {
    try {
      await httpRoute(b.id, "forward");
      notifications.show({
        color: "teal",
        message: `Booking ${b.booking_reference} forwarded to In-Charge.`,
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const httpRoute = async (id: number, action: "forward" | "reject", reason?: string) => {
    const { http } = await import("../../../lib/http");
    await http.post(`/vh/bookings/${id}/route/`, { action, reason });
  };

  const handleRejectSubmit = async () => {
    if (!rejectingBooking || !rejectReason.trim()) return;
    try {
      await httpRoute(rejectingBooking.id, "reject", rejectReason.trim());
      notifications.show({
        color: "teal",
        message: `Booking ${rejectingBooking.booking_reference} rejected.`,
      });
      setRejectingBooking(null);
      setRejectReason("");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

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
        title="Booking Review Desk"
        subtitle="Operational triage desk for Caretaker: forward eligible requisitions or reject non-compliant requests."
      />

      <Card padding="lg" withBorder>
        <DataTable<Booking>
          rows={pendingBookings}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            icon: FaInbox,
            title: "No pending requisitions awaiting review",
            description: "New online and telephonic submissions will appear here for processing.",
          }}
          columns={[
            {
              key: "reference",
              header: "Reference",
              render: (r: Booking) => (
                <Text fw={600} size="sm">
                  {r.booking_reference}
                </Text>
              ),
            },
            {
              key: "visitor",
              header: "Visitor",
              render: (r: Booking) => (
                <div>
                  <Text size="sm">{r.visitors[0]?.name ?? "Primary Guest"}</Text>
                  {r.is_offline && (
                    <Badge size="xs" color="orange" variant="outline">
                      {r.booking_source}
                    </Badge>
                  )}
                </div>
              ),
            },
            {
              key: "category",
              header: "Category",
              render: (r: Booking) => <Badge color="blue">Cat {r.visitor_category}</Badge>,
            },
            {
              key: "stay",
              header: "Stay Duration",
              render: (r: Booking) => `${r.arrival_date} to ${r.departure_date}`,
            },
            {
              key: "rooms",
              header: "Rooms / Occupants",
              render: (r: Booking) => `${r.number_of_rooms} rooms / ${r.number_of_occupants} guests`,
            },
            {
              key: "purpose",
              header: "Purpose",
              render: (r: Booking) => (
                <Text size="xs" lineClamp={2}>
                  {r.visit_purpose}
                </Text>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r: Booking) => <StatusBadge status={r.status} />,
            },
            {
              key: "actions",
              header: "Review Actions",
              align: "right",
              render: (r: Booking) => (
                <Group gap="xs" justify="flex-end">
                  <Tooltip label="Forward to VH In-Charge">
                    <Button
                      size="xs"
                      color="teal"
                      leftSection={<FaShare size={10} />}
                      onClick={() => handleForward(r)}
                    >
                      Forward
                    </Button>
                  </Tooltip>
                  <Tooltip label="Direct Rejection">
                    <Button
                      size="xs"
                      color="red"
                      variant="outline"
                      leftSection={<FaTimes size={10} />}
                      onClick={() => {
                        setRejectingBooking(r);
                        setRejectReason("");
                      }}
                    >
                      Reject
                    </Button>
                  </Tooltip>
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* Reject Modal */}
      <Modal
        opened={Boolean(rejectingBooking)}
        onClose={() => setRejectingBooking(null)}
        title="Reject Booking Requisition"
      >
        <Stack gap="md">
          <Text size="sm">
            Provide a mandatory rejection reason for <strong>{rejectingBooking?.booking_reference}</strong>:
          </Text>
          <Textarea
            label="Rejection Reason"
            required
            minRows={3}
            placeholder="No capacity for requested category on arrival dates, etc."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRejectingBooking(null)}>
              Cancel
            </Button>
            <Button color="red" onClick={handleRejectSubmit}>
              Confirm Rejection
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
