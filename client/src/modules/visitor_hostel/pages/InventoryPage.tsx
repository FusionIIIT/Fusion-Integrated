import { Alert, Badge, Card, SimpleGrid, Text, Title } from "@mantine/core";

import { useInventory } from "../api/hooks";

export default function InventoryPage() {
  const { data, isLoading, isError } = useInventory();
  if (isLoading) return <Text>Loading inventory...</Text>;
  if (isError) return <Alert color="red" title="Could not load inventory">Try again.</Alert>;
  return (
    <>
      <Title order={2} mb="md">Inventory</Title>
      {data?.length === 0
        ? <Alert title="No inventory">No active inventory items are recorded.</Alert>
        : <SimpleGrid cols={{ base: 1, md: 3 }}>
          {data?.map((item) => (
            <Card key={item.id} withBorder>
              <Text fw={600}>{item.name}</Text>
              <Text size="sm">{item.quantity} {item.unit}</Text>
              {item.below_threshold && <Badge color="red">Below threshold</Badge>}
            </Card>
          ))}
        </SimpleGrid>}
    </>
  );
}
