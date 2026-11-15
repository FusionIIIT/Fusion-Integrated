import {
  Alert,
  Button,
  Card,
  Container,
  Grid,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import { FaCheckCircle, FaHotel, FaInfoCircle } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { useCreateBooking, useVisitorCategories } from "../api/hooks";
import type { BillingResponsibility } from "../api/types";

export default function BookAccommodationPage() {
  const navigate = useNavigate();
  const { data: categories, isLoading: loadingCategories } = useVisitorCategories();
  const createBooking = useCreateBooking();

  const [visitorName, setVisitorName] = useState("");
  const [visitorEmail, setVisitorEmail] = useState("");
  const [visitorPhone, setVisitorPhone] = useState("");
  const [visitorAddress, setVisitorAddress] = useState("");
  const [visitorCategory, setVisitorCategory] = useState<string | null>(null);
  const [visitPurpose, setVisitPurpose] = useState("");
  const [checkInDate, setCheckInDate] = useState("");
  const [checkOutDate, setCheckOutDate] = useState("");
  const [numberOfRooms, setNumberOfRooms] = useState<number | string>(1);
  const [numberOfOccupants, setNumberOfOccupants] = useState<number | string>(1);
  const [billingResponsibility, setBillingResponsibility] = useState<BillingResponsibility>("VISITOR");
  const [successRef, setSuccessRef] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessRef(null);

    if (!visitorCategory) {
      setErrorMsg("Please select a visitor category.");
      return;
    }
    if (!checkInDate || !checkOutDate) {
      setErrorMsg("Please select both check-in and check-out dates.");
      return;
    }

    try {
      const res = await createBooking.mutateAsync({
        visitor_name: visitorName,
        visitor_email: visitorEmail,
        visitor_phone: visitorPhone,
        visitor_address: visitorAddress,
        visitor_category: Number(visitorCategory),
        visit_purpose: visitPurpose,
        check_in_date: checkInDate,
        check_out_date: checkOutDate,
        number_of_rooms: Number(numberOfRooms),
        number_of_occupants: Number(numberOfOccupants),
        billing_responsibility: billingResponsibility,
      });
      setSuccessRef(res.booking_reference);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || "Failed to submit booking request.";
      setErrorMsg(msg);
    }
  };

  return (
    <Container size="md" py="xl">
      <Card withBorder radius="md" p="xl" shadow="sm">
        <Group mb="md">
          <FaHotel size={28} color="#1c7ed6" />
          <div>
            <Title order={2}>Visitors Hostel Requisition</Title>
            <Text c="dimmed" size="sm">
              Standardized online booking requisition for guests and official visitors (UC-VH-001)
            </Text>
          </div>
        </Group>

        {successRef && (
          <Alert icon={<FaCheckCircle size={16} />} title="Booking Submitted Successfully" color="green" mb="lg">
            Your booking requisition has been submitted in Pending status. Reference ID: <b>{successRef}</b>.
            <Group mt="sm">
              <Button size="xs" variant="outline" color="green" onClick={() => navigate("/vh/bookings")}>
                Track My Bookings
              </Button>
            </Group>
          </Alert>
        )}

        {errorMsg && (
          <Alert icon={<FaInfoCircle size={16} />} title="Submission Error" color="red" mb="lg">
            {errorMsg}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={4} c="dimmed">Visitor Details</Title>
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <TextInput
                  label="Visitor Full Name"
                  placeholder="e.g. Prof. R. K. Sharma"
                  required
                  value={visitorName}
                  onChange={(e) => setVisitorName(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <TextInput
                  label="Visitor Email"
                  placeholder="visitor@example.com"
                  type="email"
                  value={visitorEmail}
                  onChange={(e) => setVisitorEmail(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <TextInput
                  label="Contact Phone"
                  placeholder="+91-9876543210"
                  value={visitorPhone}
                  onChange={(e) => setVisitorPhone(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Select
                  label="Visitor Category (BR-VH-019)"
                  placeholder="Select institute category"
                  required
                  disabled={loadingCategories}
                  data={categories?.map((c) => ({
                    value: String(c.id),
                    label: `${c.code} - ${c.name}`,
                  })) || []}
                  value={visitorCategory}
                  onChange={setVisitorCategory}
                />
              </Grid.Col>
              <Grid.Col span={12}>
                <Textarea
                  label="Visitor Address / Affiliation"
                  placeholder="Institution or address"
                  value={visitorAddress}
                  onChange={(e) => setVisitorAddress(e.target.value)}
                />
              </Grid.Col>
            </Grid>

            <Title order={4} c="dimmed" mt="sm">Stay & Requisition Details</Title>
            <Grid>
              <Grid.Col span={12}>
                <TextInput
                  label="Purpose of Visit"
                  placeholder="e.g. Keynote speaker at Research Symposium"
                  required
                  value={visitPurpose}
                  onChange={(e) => setVisitPurpose(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <TextInput
                  label="Expected Check-In Date"
                  type="date"
                  required
                  value={checkInDate}
                  onChange={(e) => setCheckInDate(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <TextInput
                  label="Expected Check-Out Date"
                  type="date"
                  required
                  value={checkOutDate}
                  onChange={(e) => setCheckOutDate(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <NumberInput
                  label="Number of Rooms"
                  min={1}
                  max={10}
                  required
                  value={numberOfRooms}
                  onChange={setNumberOfRooms}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <NumberInput
                  label="Number of Occupants"
                  min={1}
                  max={20}
                  required
                  value={numberOfOccupants}
                  onChange={setNumberOfOccupants}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Select
                  label="Billing Responsibility (BR-VH-002)"
                  required
                  data={[
                    { value: "VISITOR", label: "Visitor" },
                    { value: "INDENTER", label: "Indenter" },
                    { value: "INSTITUTE", label: "Institute" },
                    { value: "PROJECT", label: "Project" },
                  ]}
                  value={billingResponsibility}
                  onChange={(v) => setBillingResponsibility((v as BillingResponsibility) || "VISITOR")}
                />
              </Grid.Col>
            </Grid>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/vh/bookings")}>
                Cancel
              </Button>
              <Button type="submit" loading={createBooking.isPending}>
                Submit Requisition
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}

