import { useState } from 'react';
import { Group, Stack, Text, Button, ActionIcon, SimpleGrid, TextInput } from '@mantine/core';
import { RxTrash as Trash, RxPencil2 as Edit } from 'react-icons/rx';

export function useJsonEditor(value: any, onChange: (value: any) => void) {
  const [editMode, setEditMode] = useState(false);
  const [items, setItems] = useState(() => {
    if (!value || typeof value !== 'object') return [];
    return Object.entries(value).map(([k, v]) => ({ key: k, value: v }));
  });

  const addField = () => {
    setItems([...items, { key: '', value: '' }]);
  };

  void addField;

  const updateField = (index: number, field: 'key' | 'value', val: string) => {
    const newItems = [...items];
    if (field === 'key') newItems[index]!.key = val;
    else newItems[index]!.value = val;
    setItems(newItems);
  };

  const removeField = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    const newData: any = {};
    items.forEach(({ key, value }) => {
      if (key) newData[key] = value;
    });
    onChange(newData);
    setEditMode(false);
  };

  return (
    <Stack gap="sm">
      {!editMode ? (
        <Group justify="space-between" wrap="nowrap">
          <Text fw={500}>Policy Data</Text>
          <ActionIcon variant="light" onClick={() => setEditMode(true)}>
            <Edit size={18} />
          </ActionIcon>
        </Group>
      ) : (
        <>
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xs">
            {items.map((item, idx) => (
              <Stack key={idx} gap="xs">
                <TextInput
                  label="Key"
                  value={item.key}
                  onChange={(e) => updateField(idx, 'key', e.target.value)}
                  placeholder="Key"
                />
                <TextInput
                  label="Value"
                  value={String(item.value)}
                  onChange={(e) => updateField(idx, 'value', e.target.value)}
                  placeholder="Value"
                />
                {items.length > 2 && (
                  <ActionIcon variant="light" color="red" onClick={() => removeField(idx)}>
                    <Trash size={16} />
                  </ActionIcon>
                )}
              </Stack>
            ))}
          </SimpleGrid>
          <Group justify="space-between" mt="md">
            <Button variant="outline" onClick={() => setEditMode(false)}>Cancel</Button>
            <Button onClick={handleSave}>Save Changes</Button>
          </Group>
        </>
      )}
    </Stack>
  );
}
