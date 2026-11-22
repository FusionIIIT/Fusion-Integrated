import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBan, FaCalendarAlt, FaEdit, FaPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useBookings, useCancelBooking, useModifyBooking } from "../api/hooks";
import type { Booking } from "../api/types";

export default function MyBookingsPage() {
  const { data: bookings, isPending, error } = useBookings();
  const [cancellingBooking, setCancellingBooking] = useState<Booking | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [modifyingBooking, setModifyingBooking] = useState<Booking | null>(null);
  const [modifyPurpose, setModifyPurpose] = useState("");

  const cancelMutation = useCancelBooking(cancellingBooking?.id ?? 0);
  const modifyMutation = useModifyBooking(modifyingBooking?.id ?? 0);

  const handleCancelSubmit = async () => {
    if (!cancellingBooking || !cancelReason.trim()) return;
    try {
      await cancelMutation.mutateAsync({ reason: cancelReason.trim() });
      notifications.show({
        color: "teal",
        message: "Cancellation request submitted.",
      });
      setCancellingBooking(null);
      setCancelReason("");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleModifySubmit = async () => {
    if (!modifyingBooking || !modifyPurpose.trim()) return;
    try {
      await modifyMutation.mutateAsync({ visit_purpose: modifyPurpose.trim() });
      notifications.show({
        color: "teal",
        message: "Booking updated successfully.",
      });
      setModifyingBooking(null);
      setModifyPurpose("");
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
        title="My Booking Requisitions"
        subtitle="Track status, manage cancellation, or request modifications for your hostel requisitions."
        action={
          <Button component={Link} to="/vh/booking/new" leftSection={<FaPlus size={12} />}>
            New Requisition
          </Button>
        }
      />

      <Card padding="lg" withBorder>
        <DataTable<Booking>
          rows={bookings ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          empty={{
            icon: FaCalendarAlt,
            title: "No booking requisitions found",
            description: "Submit a new requisition to reserve rooms in the visitors hostel.",
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
              render: (r: Booking) => r.visitors[0]?.name ?? "Primary Guest",
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
              header: "Rooms / Occ",
              render: (r: Booking) => `${r.number_of_rooms} R / ${r.number_of_occupants} P`,
            },
            {
              key: "billing",
              header: "Billing",
              render: (r: Booking) => (
                <Badge variant="outline" color="gray">
                  {r.billing_responsibility}
                </Badge>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r: Booking) => <StatusBadge status={r.status} />,
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r: Booking) => {
                const canCancel = [
                  "pending",
                  "forwarded",
                  "approved",
                  "room_allotted",
                ].includes(r.status);
                const canModify = ["pending", "forwarded", "approved"].includes(r.status);

                return (
                  <Group gap="xs" justify="flex-end">
                    {canModify && (
                      <Tooltip label="Modify Purpose">
                        <ActionIcon
                          variant="subtle"
                          color="blue"
                          onClick={() => {
                            setModifyingBooking(r);
                            setModifyPurpose(r.visit_purpose);
                          }}
                        >
                          <FaEdit size={14} />
                        </ActionIcon>
                      </Tooltip>
                    )}
                    {canCancel && (
                      <Tooltip label="Request Cancellation">
                        <ActionIcon
                          variant="subtle"
                          color="red"
                          onClick={() => {
                            setCancellingBooking(r);
                            setCancelReason("");
                          }}
                        >
                          <FaBan size={14} />
                        </ActionIcon>
                      </Tooltip>
                    )}
                  </Group>
                );
              },
            },
          ]}
        />
      </Card>

      {/* Cancel Modal */}
      <Modal
        opened={Boolean(cancellingBooking)}
        onClose={() => setCancellingBooking(null)}
        title="Request Booking Cancellation"
      >
        <Stack gap="md">
          <Text size="sm">
            Cancel booking <strong>{cancellingBooking?.booking_reference}</strong>? Depending on arrival proximity, cancellation charges may apply.
          </Text>
          <Textarea
            label="Cancellation Reason"
            required
            minRows={2}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancellingBooking(null)}>
              Dismiss
            </Button>
            <Button
              color="red"
              loading={cancelMutation.isPending}
              onClick={handleCancelSubmit}
            >
              Confirm Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modify Modal */}
      <Modal
        opened={Boolean(modifyingBooking)}
        onClose={() => setModifyingBooking(null)}
        title="Modify Booking Details"
      >
        <Stack gap="md">
          <Text size="sm">
            Update purpose for booking <strong>{modifyingBooking?.booking_reference}</strong>:
          </Text>
          <TextInput
            label="Visit Purpose"
            required
            value={modifyPurpose}
            onChange={(e) => setModifyPurpose(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setModifyingBooking(null)}>
              Dismiss
            </Button>
            <Button
              color="blue"
              loading={modifyMutation.isPending}
              onClick={handleModifySubmit}
            >
              Save Updates
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
