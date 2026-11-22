import { useState } from "react";
import { Alert, Button, Card, Container, Group, Select, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDeleteMenuItem, useMenuItems, useUpsertMenuItem } from "../api/hooks";

export default function MenuManagementPage() {
  const { data: items, isLoading, error } = useMenuItems();
  const upsert = useUpsertMenuItem();
  const deleteItem = useDeleteMenuItem();

  const [day, setDay] = useState("");
  const [meal, setMeal] = useState<"breakfast" | "lunch" | "dinner">("breakfast");
  const [itemText, setItemText] = useState("");

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!day || !meal || !itemText.trim()) return;

    upsert.mutate(
      { day, meal, item: itemText.trim() },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Item Added", message: `Added ${itemText} for ${day} ${meal}.` });
          setItemText("");
        },
        onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
      }
    );
  };

  const handleDelete = (id: number) => {
    deleteItem.mutate(id, {
      onSuccess: () => notifications.show({ color: "green", title: "Item Removed", message: "Menu item deleted." }),
      onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
    });
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Menu Management" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handleAdd}>
            <Stack gap="sm">
              <Text fw={600}>Add Menu Item</Text>
              <Group grow>
                <TextInput label="Day" type="date" required value={day} onChange={(e) => setDay(e.currentTarget.value)} />
                <Select
                  label="Meal"
                  required
                  value={meal}
                  onChange={(val) => setMeal(val as "breakfast" | "lunch" | "dinner")}
                  data={[
                    { value: "breakfast", label: "Breakfast" },
                    { value: "lunch", label: "Lunch" },
                    { value: "dinner", label: "Dinner" },
                  ]}
                />
              </Group>
              <TextInput label="Menu Item" placeholder="e.g. Masala Dosa, Sambhar, Chutney" required value={itemText} onChange={(e) => setItemText(e.currentTarget.value)} />
              <Group justify="flex-end">
                <Button type="submit" loading={upsert.isPending}>Add to Menu</Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Current Menu Items ({items?.length ?? 0})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : !items || items.length === 0 ? (
            <Alert color="gray">No menu items listed yet.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Day</Table.Th>
                  <Table.Th>Meal</Table.Th>
                  <Table.Th>Dish / Items</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {items.map((i) => (
                  <Table.Tr key={i.id}>
                    <Table.Td>{i.day}</Table.Td>
                    <Table.Td style={{ textTransform: "capitalize" }}>{i.meal}</Table.Td>
                    <Table.Td>{i.item}</Table.Td>
                    <Table.Td>
                      <Button size="xs" color="red" variant="subtle" onClick={() => handleDelete(i.id)} loading={deleteItem.isPending}>Delete</Button>
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
