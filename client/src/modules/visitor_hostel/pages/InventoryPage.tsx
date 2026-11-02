import { Card, Title, Table, Badge, Button, NumberInput, Group } from '@mantine/core';
import { useState } from 'react';

interface InventoryItem {
  name: string;
  code: string;
  currentQuantity: number;
  threshold: number;
}

const InventoryPage = () => {
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  
  // This is a mock function to simulate fetching data from server. Replace it with your actual API call.
  const fetchData = async () => {
    return new Promise((resolve) => {
      setTimeout(() => resolve([
        { name: 'Item1', code: 'C001', currentQuantity: 5, threshold: 10 },
        { name: 'Item2', code: 'D002', currentQuantity: 7, threshold: 8 },
      ]), 1000);
    });
  };
  
  const handleReplenish = () => {
    // Handle replenishment logic here. This is a placeholder function.
    console.log('Handle Replenishment');
  }

  return (
    <Card shadow="sm" padding="lg">
      <Title order={2}>Inventory</Title>
      
      {/* Fetch data on component mount */}
      {inventoryItems.length === 0 && fetchData().then(setInventoryItems)}

      <Table striped highlightOnHover withBorderInside>
        <thead>
          <tr>
            <th>Name</th>
            <th>Code</th>
            <th>Current Quantity</th>
            <th>Threshold</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {inventoryItems.map((item, index) => (
            <tr key={index}>
              <td>{item.name}</td>
              <td>{item.code}</td>
              <td>{item.currentQuantity}</td>
              <td>{item.threshold}</td>
              <td>
                {item.currentQuantity < item.threshold ? (
                  <Badge color="red" variant="light">LOW STOCK</Badge>
                ) : (
                  <Badge color="green" variant="light">OK</Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      
      {/* Replenish button */}
      <Group position="right" mt="md">
        <Button onClick={handleReplenish}>Request Replenishment</Button>
      </Group>
    </Card>
  );
};

export default InventoryPage;
