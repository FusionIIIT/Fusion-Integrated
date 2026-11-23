import React, { useState } from 'react';
import { Paper, Title, TextInput, NumberInput, Select, Button } from '@mantine/core';

interface IndentFormData {
  indent_number: string;
  title: string;
  department: string;
  justification: string;
  total_estimated_cost: number;
  priority: string;
}

interface IndentFormProps {
  onSubmit: (indent: IndentFormData) => void;
  onCancel: () => void;
  initialData?: IndentFormData | null;
}

const IndentForm: React.FC<IndentFormProps> = ({ onSubmit, onCancel, initialData }) => {
  const [indent_number, setIndentNumber] = useState(initialData?.indent_number ?? '');
  const [title, setTitle] = useState(initialData?.title ?? '');
  const [department, setDepartment] = useState(initialData?.department ?? '');
  const [justification, setJustification] = useState(initialData?.justification ?? '');
  const [total_estimated_cost, setTotalEstimatedCost] = useState<number>(Number(initialData?.total_estimated_cost ?? 0));
  const [priority, setPriority] = useState(initialData?.priority ?? 'normal');

  const handleSubmit = () => {
    onSubmit({ indent_number, title, department, justification, total_estimated_cost, priority });
  };

  return (
    <Paper shadow="sm" p="lg">
      <Title order={2} mb="md">{initialData ? 'Edit Indent' : 'Create Indent'}</Title>
      <TextInput label="Indent Number" value={indent_number} onChange={(e) => setIndentNumber(e.currentTarget.value)} required mb="sm" />
      <TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} required mb="sm" />
      <TextInput label="Department" value={department} onChange={(e) => setDepartment(e.currentTarget.value)} required mb="sm" />
      <TextInput label="Justification" value={justification} onChange={(e) => setJustification(e.currentTarget.value)} required mb="sm" />
      <NumberInput
        label="Total Estimated Cost"
        value={total_estimated_cost}
        onChange={(value) => setTotalEstimatedCost(Number(value) || 0)}
        required
        mb="sm"
      />
      <Select
        label="Priority"
        value={priority}
        onChange={(value) => setPriority(value ?? 'normal')}
        data={['low', 'normal', 'high', 'urgent']}
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

export default IndentForm;
