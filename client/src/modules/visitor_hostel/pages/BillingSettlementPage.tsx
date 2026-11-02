import { Card, Title, Table, Badge, Button, Group, Text } from '@mantine/core';
import React from 'react';

interface BillingSettlementPageProps {
  roomCharges: number;
  mealCharges: number;
  cancellationFee: number;
}

const BillingSettlementPage: React.FC<BillingSettlementPageProps> = ({ roomCharges, mealCharges, cancellationFee }) => {
  const totalAmount = roomCharges + mealCharges + cancellationFee;
  
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Title order={2}>Billing Settlement</Title>
      
      <Table mt="md">
        <thead>
          <tr>
            <th>Description</th>
            <th>Amount</th>
          </tr>
        </thead>
        
        <tbody>
          <tr>
            <td>Room Charges</td>
            <td><Badge color="blue" variant="light">${roomCharges}</Badge></td>
          </tr>
          
          <tr>
            <td>Meal Charges</td>
            <td><Badge color="green" variant="light">${mealCharges}</Badge></td>
          </tr>
          
          <tr>
            <td>Cancellation Fee</td>
            <td><Badge color="red" variant="light">${cancellationFee}</Badge></td>
          </tr>
        </tbody>
      </Table>
      
      <Group position="right" mt="md">
        <Text size="lg" weight={500}>Total: <Badge color="violet" variant="light">${totalAmount}</Badge></Text>
        
        {/* This assumes that the payment mode is always 'Cash' */}
        <Button disabled={true}>Record Cash Settlement</Button>
      </Group>
    </Card>
  );
};

export default BillingSettlementPage;
