import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUtensils } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBookMeal, useBookingMeals, useBookings } from "../api/hooks";
import type { MealBooking, MealOption } from "../api/types";

export default function MessManagementPage() {
  const { data: bookings, error } = useBookings({ status: "checked_in" });
  const [selectedBookingId, setSelectedBookingId] = useState<string>("");
  const [mealDate, setMealDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [mealOption, setMealOption] = useState<MealOption>("full_day");
  const [individualType, setIndividualType] = useState<string>("breakfast");
  const [addOnType, setAddOnType] = useState<string>("tea");
  const [quantity, setQuantity] = useState<number>(1);

  const bId = Number(selectedBookingId) || 0;
  const { data: meals, isPending: mealsLoading } = useBookingMeals(bId);
  const bookMealMutation = useBookMeal(bId);

  const handleBookMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bId) {
      notifications.show({ color: "red", message: "Please select an active guest booking." });
      return;
    }

    try {
      await bookMealMutation.mutateAsync({
        meal_date: mealDate,
        meal_option: mealOption,
        individual_type: mealOption === "individual" ? individualType : undefined,
        add_on_type: mealOption === "add_on" ? addOnType : undefined,
        quantity,
      });
      notifications.show({ color: "teal", message: "Meal order booked successfully." });
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
    <Container size="lg">
      <PageHeader
        title="Mess & Dining Services"
        subtitle="Record meal orders and track catering consumption for checked-in hostel guests."
      />

      <Stack gap="lg">
        <Card padding="lg" withBorder component="form" onSubmit={handleBookMeal}>
          <Stack gap="md">
            <Select
              label="Select Active Guest Stay"
              placeholder="Choose checked-in guest"
              required
              data={
                bookings?.map((b) => ({
                  value: String(b.id),
                  label: `${b.booking_reference} - ${b.visitors[0]?.name ?? "Guest"} (Rooms: ${b.allotments.map((a) => a.room.room_number).join(",")})`,
                })) ?? []
              }
              value={selectedBookingId}
              onChange={(val) => setSelectedBookingId(val || "")}
            />

            <Group grow>
              <TextInput
                label="Meal Date"
                type="date"
                required
                value={mealDate}
                onChange={(e) => setMealDate(e.currentTarget.value)}
              />
              <Select
                label="Meal Package / Option"
                required
                data={[
                  { value: "full_day", label: "Full Day Dining Package (₹368)" },
                  { value: "individual", label: "Individual Meal" },
                  { value: "add_on", label: "Special Add-on / Beverage" },
                ]}
                value={mealOption}
                onChange={(val) => setMealOption((val as MealOption) || "full_day")}
              />
            </Group>

            {mealOption === "individual" && (
              <Select
                label="Meal Course"
                required
                data={[
                  { value: "breakfast", label: "Breakfast (₹65)" },
                  { value: "lunch", label: "Lunch (₹138)" },
                  { value: "dinner", label: "Dinner (₹165)" },
                ]}
                value={individualType}
                onChange={(val) => setIndividualType(val || "breakfast")}
              />
            )}

            {mealOption === "add_on" && (
              <Select
                label="Special Add-on Item"
                required
                data={[
                  { value: "tea", label: "Special Tea / Coffee" },
                  { value: "cold_drink", label: "Cold Drinks" },
                  { value: "sweet", label: "Special Desserts / Sweets" },
                ]}
                value={addOnType}
                onChange={(val) => setAddOnType(val || "tea")}
              />
            )}

            <NumberInput
              label="Meal Quantity"
              min={1}
              max={20}
              required
              value={quantity}
              onChange={(val) => setQuantity(Number(val) || 1)}
            />

            <Group justify="flex-end" mt="sm">
              <Button
                type="submit"
                loading={bookMealMutation.isPending}
                leftSection={<FaUtensils size={14} />}
              >
                Record Meal Order
              </Button>
            </Group>
          </Stack>
        </Card>

        {bId > 0 && (
          <Card padding="lg" withBorder>
            <Text fw={600} mb="sm">
              Meal Orders History for Selected Stay
            </Text>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Date</Table.Th>
                  <Table.Th>Option</Table.Th>
                  <Table.Th>Details</Table.Th>
                  <Table.Th>Quantity</Table.Th>
                  <Table.Th>Rate (₹)</Table.Th>
                  <Table.Th>Amount (₹)</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {mealsLoading ? (
                  <Table.Tr>
                    <Table.Td colSpan={6}>Loading orders...</Table.Td>
                  </Table.Tr>
                ) : meals?.length ? (
                  meals.map((m: MealBooking) => (
                    <Table.Tr key={m.id}>
                      <Table.Td>{m.meal_date}</Table.Td>
                      <Table.Td>
                        <Badge>{m.meal_option}</Badge>
                      </Table.Td>
                      <Table.Td>{m.individual_type || m.add_on_type || "Standard"}</Table.Td>
                      <Table.Td>{m.quantity}</Table.Td>
                      <Table.Td>₹{m.rate}</Table.Td>
                      <Table.Td>
                        <Text fw={600}>₹{m.amount}</Text>
                      </Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={6}>
                      <Text c="dimmed">No meal orders recorded for this stay.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        )}
      </Stack>
    </Container>
  );
}
