import React, { useState } from 'react';
import { Paper, Title, TextInput, NumberInput, Button } from '@mantine/core';

interface StockItemFormData {
  item_code: string;
  name: string;
  category: string;
  unit: string;
  available_quantity: number;
}

interface StockItemFormProps {
  onSubmit: (item: StockItemFormData) => void;
  onCancel: () => void;
  initialData?: StockItemFormData | null;
}

const StockItemForm: React.FC<StockItemFormProps> = ({ onSubmit, onCancel, initialData }) => {
  const [item_code, setItemCode] = useState(initialData?.item_code ?? '');
  const [name, setName] = useState(initialData?.name ?? '');
  const [category, setCategory] = useState(initialData?.category ?? '');
  const [unit, setUnit] = useState(initialData?.unit ?? '');
  const [available_quantity, setAvailableQuantity] = useState<number>(Number(initialData?.available_quantity ?? 0));

  const handleSubmit = () => {
    onSubmit({ item_code, name, category, unit, available_quantity });
  };

  return (
    <Paper shadow="sm" p="lg">
      <Title order={2} mb="md">{initialData ? 'Edit Stock Item' : 'Create Stock Item'}</Title>
      <TextInput label="Item Code" value={item_code} onChange={(e) => setItemCode(e.currentTarget.value)} required mb="sm" />
      <TextInput label="Name" value={name} onChange={(e) => setName(e.currentTarget.value)} required mb="sm" />
      <TextInput label="Category" value={category} onChange={(e) => setCategory(e.currentTarget.value)} required mb="sm" />
      <TextInput label="Unit" value={unit} onChange={(e) => setUnit(e.currentTarget.value)} required mb="sm" />
      <NumberInput
        label="Available Quantity"
        value={available_quantity}
        onChange={(value) => setAvailableQuantity(Number(value) || 0)}
        required
        mb="lg"
      />
      <Button type="submit" onClick={handleSubmit} mr="md">
        Submit
      </Button>
      <Button variant="default" onClick={onCancel}>Cancel</Button>
    </Paper>
  );
};

export default StockItemForm;
