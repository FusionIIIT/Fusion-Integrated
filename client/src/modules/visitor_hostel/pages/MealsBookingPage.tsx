import { useState } from 'react';
import { Card, Title, Checkbox, NumberInput, Button, Table, Group } from '@mantine/core';

const MealsBookingPage = () => {
  const [breakfastChecked, setBreakfastChecked] = useState(false);
  const [lunchChecked, setLunchChecked] = useState(false);
  const [dinnerChecked, setDinnerChecked] = useState(false);
  const [teaCount, setTeaCount] = useState(0);
  const [milkCount, setMilkCount] = useState(0);
  
  // Assuming the cost of meals and add-ons are constants for simplicity. In a real application, these would be dynamic based on business rules.
  const mealCost = 10;
  const teaCost = 2;
  const milkCost = 1;

  const totalMealCost = (breakfastChecked || lunchChecked || dinnerChecked) ? mealCost : 0;
  const totalTeaCost = teaCount * teaCost;
  const totalMilkCost = milkCount * milkCost;
  
  // Assuming the cost of meals and add-ons are constants for simplicity. In a real application, these would be dynamic based on business rules.
  const totalCost = totalMealCost + totalTeaCost + totalMilkCost;

  return (
    <Card>
      <Title order={2}>Meals Booking</Title>
      
      <Checkbox label="Full Day" />
      {/* You can use RadioGroup or individual Checkboxes for breakfast, lunch and dinner */}
      
      <NumberInput label="Tea Count" value={teaCount} onChange={setTeaCount} />
      <NumberInput label="Milk Count" value={milkCount} onChange={setMilkCount} />
      {/* You can use a Table to display the meals, tea and milk counts */}
      
      <Group position="right" mt="md">
        <Button variant="outline" color="red">Cancel</Button>
        <Button variant="filled" color="blue">Book Meals</Button>
      </Group>
    </Card>
  );
};

export default MealsBookingPage;
