import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Select,
  Stack,
  Switch,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPaperPlane } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateBooking, useCreateOfflineBooking } from "../api/hooks";
import type { BillingResponsibility, VisitorCategory } from "../api/types";

export default function NewBookingPage() {
  const navigate = useNavigate();
  const { can } = useAuth();
  const canOffline = can("vh.booking.offline");

  const [isOffline, setIsOffline] = useState(false);
  const [offlineSource, setOfflineSource] = useState<"walk_in" | "telephonic">("walk_in");
  const [visitorName, setVisitorName] = useState("");
  const [visitorEmail, setVisitorEmail] = useState("");
  const [visitorPhone, setVisitorPhone] = useState("");
  const [visitorCategory, setVisitorCategory] = useState<VisitorCategory>("A");
  const [visitPurpose, setVisitPurpose] = useState("");
  const [arrivalDate, setArrivalDate] = useState("");
  const [departureDate, setDepartureDate] = useState("");
  const [numberOfRooms, setNumberOfRooms] = useState<number>(1);
  const [numberOfOccupants, setNumberOfOccupants] = useState<number>(1);
  const [billingResp, setBillingResp] = useState<BillingResponsibility>("visitor");

  const createOnline = useCreateBooking();
  const createOffline = useCreateOfflineBooking();

  const isSubmitting = createOnline.isPending || createOffline.isPending;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!visitorName.trim() || !arrivalDate || !departureDate) {
      notifications.show({
        color: "red",
        message: "Please fill in visitor name, arrival date, and departure date.",
      });
      return;
    }

    try {
      if (isOffline && canOffline) {
        await createOffline.mutateAsync({
          visitor_name: visitorName.trim(),
          visitor_email: visitorEmail.trim(),
          visitor_phone: visitorPhone.trim(),
          visitor_category: visitorCategory,
          visit_purpose: visitPurpose.trim(),
          arrival_date: arrivalDate,
          departure_date: departureDate,
          number_of_rooms: Number(numberOfRooms) || 1,
          number_of_occupants: Number(numberOfOccupants) || 1,
          billing_responsibility: billingResp,
          booking_source: offlineSource,
        });
      } else {
        await createOnline.mutateAsync({
          visitor_name: visitorName.trim(),
          visitor_email: visitorEmail.trim(),
          visitor_phone: visitorPhone.trim(),
          visitor_category: visitorCategory,
          visit_purpose: visitPurpose.trim(),
          arrival_date: arrivalDate,
          departure_date: departureDate,
          number_of_rooms: Number(numberOfRooms) || 1,
          number_of_occupants: Number(numberOfOccupants) || 1,
          billing_responsibility: billingResp,
        });
      }

      notifications.show({
        color: "teal",
        message: "Booking requisition submitted successfully.",
      });
      navigate("/vh/my-bookings");
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="New Booking Requisition"
        subtitle="Submit a room requisition for institute visitors, guests, or official events."
      />

      <Card padding="lg" withBorder component="form" onSubmit={handleSubmit}>
        <Stack gap="md">
          {canOffline && (
            <Group justify="space-between">
              <Switch
                label="Offline Booking (Walk-in / Telephonic)"
                checked={isOffline}
                onChange={(e) => setIsOffline(e.currentTarget.checked)}
              />
              {isOffline && (
                <Select
                  label="Booking Source"
                  data={[
                    { value: "walk_in", label: "Walk-in Desk" },
                    { value: "telephonic", label: "Telephonic Requisition" },
                  ]}
                  value={offlineSource}
                  onChange={(val) => setOfflineSource((val as "walk_in" | "telephonic") || "walk_in")}
                />
              )}
            </Group>
          )}

          <TextInput
            label="Primary Visitor Name"
            placeholder="Dr. John Doe"
            required
            value={visitorName}
            onChange={(e) => setVisitorName(e.currentTarget.value)}
          />

          <Group grow>
            <TextInput
              label="Visitor Email"
              placeholder="visitor@example.com"
              type="email"
              value={visitorEmail}
              onChange={(e) => setVisitorEmail(e.currentTarget.value)}
            />
            <TextInput
              label="Visitor Phone"
              placeholder="+91 9876543210"
              value={visitorPhone}
              onChange={(e) => setVisitorPhone(e.currentTarget.value)}
            />
          </Group>

          <Group grow>
            <Select
              label="Visitor Category"
              required
              data={[
                { value: "A", label: "Category A - Institute Guest / Board Member" },
                { value: "B", label: "Category B - Invited Academic / Examiner" },
                { value: "C", label: "Category C - Official Delegations" },
                { value: "D", label: "Category D - Personal / Student Guests" },
              ]}
              value={visitorCategory}
              onChange={(val) => setVisitorCategory((val as VisitorCategory) || "A")}
            />
            <Select
              label="Billing Responsibility"
              required
              data={[
                { value: "visitor", label: "Visitor Self-Pay" },
                { value: "indenter", label: "Indenter Personal Account" },
                { value: "institute", label: "Institute Core Budget" },
                { value: "project", label: "Project Account" },
              ]}
              value={billingResp}
              onChange={(val) => setBillingResp((val as BillingResponsibility) || "visitor")}
            />
          </Group>

          <Group grow>
            <TextInput
              label="Arrival Date"
              type="date"
              required
              value={arrivalDate}
              onChange={(e) => setArrivalDate(e.currentTarget.value)}
            />
            <TextInput
              label="Departure Date"
              type="date"
              required
              value={departureDate}
              onChange={(e) => setDepartureDate(e.currentTarget.value)}
            />
          </Group>

          <Group grow>
            <NumberInput
              label="Number of Rooms"
              min={1}
              max={10}
              required
              value={numberOfRooms}
              onChange={(val) => setNumberOfRooms(Number(val) || 1)}
            />
            <NumberInput
              label="Total Occupants"
              min={1}
              max={20}
              required
              value={numberOfOccupants}
              onChange={(val) => setNumberOfOccupants(Number(val) || 1)}
            />
          </Group>

          <Textarea
            label="Visit Purpose & Remarks"
            placeholder="Official lecture, research collaboration, etc."
            required
            minRows={3}
            value={visitPurpose}
            onChange={(e) => setVisitPurpose(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button
              type="submit"
              loading={isSubmitting}
              leftSection={<FaPaperPlane size={14} />}
            >
              Submit Requisition
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
