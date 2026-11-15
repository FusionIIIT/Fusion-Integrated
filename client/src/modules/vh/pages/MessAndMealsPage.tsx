import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Loader,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  FaCheckCircle,
  FaCoffee,
  FaConciergeBell,
  FaInfoCircle,
  FaPlus,
  FaUtensils,
} from "react-icons/fa";

import { useBookings, useCreateMealBooking, useMealBookings } from "../api/hooks";
import type { MealAddOn, MealType } from "../api/types";

export default function MessAndMealsPage() {
  const { data: bookings } = useBookings();
  const { data: meals, isLoading: loadingMeals, refetch: refetchMeals } = useMealBookings();
  const createMeal = useCreateMealBooking();

  // Active bookings eligible for meal bookings (CHECKED_IN or ROOM_ALLOTTED)
  const activeBookings = (bookings || []).filter(
    (b) => b.status === "CHECKED_IN" || b.status === "ROOM_ALLOTTED",
  );

  // Form states
  const [selectedBookingId, setSelectedBookingId] = useState<string | null>(null);
  const [mealDate, setMealDate] = useState(new Date().toISOString().split("T")[0]);
  const [mealType, setMealType] = useState<MealType>("BREAKFAST");
  const [addOn, setAddOn] = useState<MealAddOn>("NONE");
  const [numPersons, setNumPersons] = useState<number | string>(1);
  const [filterBookingId, setFilterBookingId] = useState<string | null>(null);

  const [formSuccess, setFormSuccess] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreateMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSuccess(false);
    setFormError(null);

    if (!selectedBookingId) {
      setFormError("Please select a guest booking.");
      return;
    }
    if (!mealDate) {
      setFormError("Please select a date.");
      return;
    }

    try {
      await createMeal.mutateAsync({
        booking: Number(selectedBookingId),
        date: mealDate,
        meal_type: mealType,
        add_on: addOn,
        number_of_persons: Number(numPersons),
      });
      setFormSuccess(true);
      // Reset form fields
      setNumPersons(1);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message || "Failed to record meal booking.";
      setFormError(msg);
    }
  };

  // Filtered meals list
  const filteredMeals = (meals || []).filter((m) => {
    if (!filterBookingId) return true;
    return m.booking === Number(filterBookingId);
  });

  // Today's meals count
  const todayStr = new Date().toISOString().split("T")[0];
  const todayMealsCount = (meals || []).filter((m) => m.date === todayStr).length;
  const totalMealRevenue = (meals || []).reduce(
    (sum, m) => sum + parseFloat(m.total_amount || "0"),
    0,
  );

  const getMealBadgeColor = (type: MealType) => {
    switch (type) {
      case "BREAKFAST":
        return "yellow";
      case "LUNCH":
        return "orange";
      case "DINNER":
        return "indigo";
      case "FULL_DAY":
        return "teal";
      default:
        return "gray";
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Visitors Hostel Mess & Meals Management</Title>
            <Text c="dimmed" size="sm">
              Schedule meals for residing hostel guests and track automatic billing integration (UC-VH-007, BR-VH-007)
            </Text>
          </div>
          <Button variant="default" onClick={() => refetchMeals()} leftSection={<FaUtensils />}>
            Refresh
          </Button>
        </Group>

        {/* Overview Stats */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Meals Logged
                </Text>
                <Title order={3}>{(meals || []).length}</Title>
              </div>
              <FaUtensils size={26} color="#228be6" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Meals Scheduled Today
                </Text>
                <Title order={3}>{todayMealsCount}</Title>
              </div>
              <FaConciergeBell size={26} color="#fd7e14" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Meal Charges
                </Text>
                <Title order={3}>₹{totalMealRevenue.toFixed(2)}</Title>
              </div>
              <FaCoffee size={26} color="#12b886" />
            </Group>
          </Paper>
        </SimpleGrid>

        <Grid gutter="md">
          {/* Left Column: Meal Booking Form */}
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Card withBorder radius="md" p="md" shadow="xs">
              <Group mb="sm">
                <FaConciergeBell size={20} color="#e67700" />
                <Title order={4}>Book Meal for Guest</Title>
              </Group>
              <Text size="xs" c="dimmed" mb="md">
                Meals can be scheduled for residing guests who are allotted or checked in.
              </Text>

              {formSuccess && (
                <Alert
                  icon={<FaCheckCircle size={16} />}
                  title="Meal Recorded"
                  color="teal"
                  mb="md"
                  withCloseButton
                  onClose={() => setFormSuccess(false)}
                >
                  Meal charges recorded and added to the guest stay ledger!
                </Alert>
              )}

              {formError && (
                <Alert
                  icon={<FaInfoCircle size={16} />}
                  title="Error"
                  color="red"
                  mb="md"
                  withCloseButton
                  onClose={() => setFormError(null)}
                >
                  {formError}
                </Alert>
              )}

              <form onSubmit={handleCreateMeal}>
                <Stack gap="sm">
                  <Select
                    label="Select Guest / Booking"
                    placeholder="Choose active booking..."
                    required
                    data={activeBookings.map((b) => ({
                      value: String(b.id),
                      label: `${b.booking_reference} - ${b.visitor_name} (${b.status})`,
                    }))}
                    value={selectedBookingId}
                    onChange={setSelectedBookingId}
                  />

                  <TextInput
                    type="date"
                    label="Meal Date"
                    required
                    value={mealDate}
                    onChange={(e) => setMealDate(e.target.value)}
                  />

                  <Select
                    label="Meal Type"
                    required
                    data={[
                      { value: "BREAKFAST", label: "Breakfast" },
                      { value: "LUNCH", label: "Lunch" },
                      { value: "DINNER", label: "Dinner" },
                      { value: "FULL_DAY", label: "Full Day Meals" },
                    ]}
                    value={mealType}
                    onChange={(val) => setMealType((val as MealType) || "BREAKFAST")}
                  />

                  <Select
                    label="Beverage / Add-On"
                    data={[
                      { value: "NONE", label: "None" },
                      { value: "TEA", label: "Tea" },
                      { value: "MILK", label: "Milk" },
                    ]}
                    value={addOn}
                    onChange={(val) => setAddOn((val as MealAddOn) || "NONE")}
                  />

                  <NumberInput
                    label="Number of Persons"
                    min={1}
                    max={20}
                    required
                    value={numPersons}
                    onChange={setNumPersons}
                  />

                  <Button
                    type="submit"
                    color="orange"
                    leftSection={<FaPlus size={14} />}
                    loading={createMeal.isPending}
                    mt="xs"
                  >
                    Confirm Meal Booking
                  </Button>
                </Stack>
              </form>
            </Card>
          </Grid.Col>

          {/* Right Column: Meal Records Table */}
          <Grid.Col span={{ base: 12, md: 7 }}>
            <Card withBorder radius="md" p="md">
              <Group justify="space-between" mb="md">
                <div>
                  <Title order={4}>Mess Schedule & Ledger</Title>
                  <Text size="xs" c="dimmed">
                    Complete log of scheduled meals and accrued charges
                  </Text>
                </div>
                <Select
                  size="xs"
                  placeholder="Filter by Booking"
                  clearable
                  data={(bookings || []).map((b) => ({
                    value: String(b.id),
                    label: `${b.booking_reference} (${b.visitor_name})`,
                  }))}
                  value={filterBookingId}
                  onChange={setFilterBookingId}
                />
              </Group>

              {loadingMeals ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : filteredMeals.length === 0 ? (
                <Alert icon={<FaInfoCircle size={16} />} title="No meal records" color="blue">
                  No meals have been logged for this selection yet.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Booking</Table.Th>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Meal Type</Table.Th>
                      <Table.Th>Add-On</Table.Th>
                      <Table.Th>Persons</Table.Th>
                      <Table.Th>Rate</Table.Th>
                      <Table.Th>Total</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {filteredMeals.map((m) => (
                      <Table.Tr key={m.id}>
                        <Table.Td>#{m.id}</Table.Td>
                        <Table.Td>
                          <Text fw={500} size="xs">Booking #{m.booking}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{m.date}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge size="xs" color={getMealBadgeColor(m.meal_type)}>
                            {m.meal_type}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge size="xs" variant="outline" color={m.add_on !== "NONE" ? "teal" : "gray"}>
                            {m.add_on}
                          </Badge>
                        </Table.Td>
                        <Table.Td>{m.number_of_persons}</Table.Td>
                        <Table.Td>₹{m.rate}</Table.Td>
                        <Table.Td>
                          <Text fw={600} size="sm" c="blue">
                            ₹{m.total_amount}
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  );
}
