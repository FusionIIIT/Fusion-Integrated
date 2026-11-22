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
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaInbox, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBookings } from "../api/hooks";
import type { Booking } from "../api/types";

export default function ExecutiveApprovalsPage() {
  const { data: bookings, isPending, error } = useBookings();
  const [rejectingBooking, setRejectingBooking] = useState<Booking | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const forwardedBookings = (bookings ?? []).filter(
    (b) => b.status === "forwarded" || b.status === "forwarded_offline"
  );

  const handleApprove = async (b: Booking) => {
    const { http } = await import("../../../lib/http");
    try {
      await http.post(`/vh/bookings/${b.id}/decide/`, { action: "approve" });
      notifications.show({
        color: "teal",
        message: `Booking ${b.booking_reference} approved. Caretaker can now allot rooms.`,
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleRejectSubmit = async () => {
    if (!rejectingBooking || !rejectReason.trim()) return;
    const { http } = await import("../../../lib/http");
    try {
      await http.post(`/vh/bookings/${rejectingBooking.id}/decide/`, {
        action: "reject",
        reason: rejectReason.trim(),
      });
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
        title="Executive Approval Desk"
        subtitle="VH In-Charge decision terminal: approve or reject forwarded booking requisitions."
      />

      <Card padding="lg" withBorder>
        <DataTable<Booking>
          rows={forwardedBookings}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            icon: FaInbox,
            title: "No forwarded requisitions awaiting executive decision",
            description: "Requisitions forwarded by the caretaker will appear here.",
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
                  <Text size="sm">{r.visitors[0]?.name ?? "Guest"}</Text>
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
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r: Booking) => (
                <Group gap="xs" justify="flex-end">
                  <Button
                    size="xs"
                    color="teal"
                    leftSection={<FaCheck size={10} />}
                    onClick={() => handleApprove(r)}
                  >
                    Approve
                  </Button>
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
        title="Reject Forwarded Requisition"
      >
        <Stack gap="md">
          <Text size="sm">
            Provide formal rejection rationale for <strong>{rejectingBooking?.booking_reference}</strong>:
          </Text>
          <Textarea
            label="Rejection Reason"
            required
            minRows={3}
            placeholder="Hostel fully reserved for institute foundation day..."
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
