import { useEffect, useState } from "react";
import { Badge, Card, Container, Group, Loader, Stack, Table, Text, Title } from "@mantine/core";
import { mmsApi } from "../api";
import type { DailyMenuItem } from "../types";

export default function MenuPage() {
  const [menu, setMenu] = useState<DailyMenuItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMenu() {
      try {
        const data = await mmsApi.getWeeklyMenu();
        setMenu(data);
      } catch (err) {
        console.error("Failed to load menu", err);
      } finally {
        setLoading(false);
      }
    }
    fetchMenu();
  }, []);

  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <div>
          <Title order={2}>Mess Weekly Menu</Title>
          <Text c="dimmed">Official published menu schedule for all mess meals.</Text>
        </div>

        <Card withBorder radius="md">
          {loading ? (
            <Group justify="center" py="xl"><Loader /></Group>
          ) : menu.length === 0 ? (
            <Text c="dimmed" py="xl" ta="center">No menu items found.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Day of Week</Table.Th>
                  <Table.Th>Meal</Table.Th>
                  <Table.Th>Menu Items</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {menu.map((m) => (
                  <Table.Tr key={m.id}>
                    <Table.Td fw={500}>{m.day_of_week}</Table.Td>
                    <Table.Td>
                      <Badge size="sm" variant="light" color={m.meal_time === "BREAKFAST" ? "yellow" : m.meal_time === "LUNCH" ? "teal" : "indigo"}>
                        {m.meal_time}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{m.items}</Table.Td>
                    <Table.Td>
                      <Badge size="xs" color={m.is_active ? "green" : "gray"}>
                        {m.is_active ? "Active" : "Archived"}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
