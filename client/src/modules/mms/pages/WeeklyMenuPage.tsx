import { Alert, Badge, Card, Container, Group, SimpleGrid, Stack, Table, Text } from "@mantine/core";
import { FaUtensils } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMenuItems } from "../api/hooks";

export default function WeeklyMenuPage() {
  const { data: items, isLoading, error } = useMenuItems();

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  // Group by day and meal
  const dayGroups: Record<string, Record<string, string[]>> = {};
  items?.forEach((item) => {
    if (!dayGroups[item.day]) {
      dayGroups[item.day] = { breakfast: [], lunch: [], dinner: [] };
    }
    dayGroups[item.day][item.meal]?.push(item.item);
  });

  const sortedDays = Object.keys(dayGroups).sort();

  return (
    <Container size="lg">
      <PageHeader title="Weekly Mess Menu" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Current schedule of meals for breakfast, lunch, and dinner.
        </Text>

        {isLoading ? (
          <Text c="dimmed">Loading menu...</Text>
        ) : sortedDays.length === 0 ? (
          <Alert color="gray" icon={<FaUtensils />}>
            No menu items published for this week yet.
          </Alert>
        ) : (
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            {sortedDays.map((day) => (
              <Card key={day} withBorder padding="md">
                <Text fw={700} size="lg" mb="xs">
                  {new Date(day).toLocaleDateString(undefined, {
                    weekday: "long",
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </Text>
                <Stack gap="xs">
                  <div>
                    <Badge color="orange" size="sm" mb={4}>
                      Breakfast
                    </Badge>
                    <Text size="sm">
                      {dayGroups[day].breakfast.join(", ") || "No items listed"}
                    </Text>
                  </div>
                  <div>
                    <Badge color="blue" size="sm" mb={4}>
                      Lunch
                    </Badge>
                    <Text size="sm">
                      {dayGroups[day].lunch.join(", ") || "No items listed"}
                    </Text>
                  </div>
                  <div>
                    <Badge color="teal" size="sm" mb={4}>
                      Dinner
                    </Badge>
                    <Text size="sm">
                      {dayGroups[day].dinner.join(", ") || "No items listed"}
                    </Text>
                  </div>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Stack>
    </Container>
  );
}
