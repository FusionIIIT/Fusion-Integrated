import { useState } from "react";
import { NumberInput, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useCreateInventoryItem } from "../api/hooks";

interface Props {
  opened: boolean;
  onClose: () => void;
  departmentId: number;
}

export function InsertStockModal({ opened, onClose, departmentId }: Props) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState<number | string>(10);
  const [unit, setUnit] = useState("pieces");

  const createItem = useCreateInventoryItem();

  const handleSubmit = async () => {
    if (!name.trim() || Number(quantity) < 0) return;
    try {
      await createItem.mutateAsync({
        department: departmentId,
        name: name.trim(),
        quantity: Number(quantity),
        unit: unit.trim(),
      });
      notifications.show({
        title: "Item Added",
        message: `${name} has been added to inventory.`,
        color: "teal",
      });
      setName("");
      setQuantity(10);
      onClose();
    } catch (e) {
      notifications.show({
        title: "Failed to Add Item",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Add Inventory Item"
      subtitle="Register an item and initial quantity into department stock"
      onSubmit={handleSubmit}
      submitting={createItem.isPending}
      disabled={!name.trim()}
    >
      <Stack gap="sm">
        <TextInput
          label="Item Name"
          placeholder="e.g. Breadboards, HDMI Cables, A4 Paper"
          required
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
        />
        <NumberInput
          label="Initial Quantity"
          required
          min={0}
          value={quantity}
          onChange={setQuantity}
        />
        <TextInput
          label="Unit"
          placeholder="e.g. pieces, packets, boxes"
          value={unit}
          onChange={(e) => setUnit(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
