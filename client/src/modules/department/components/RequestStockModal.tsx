import { useState } from "react";
import { NumberInput, Select, Stack } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useCreateStockRequest, useInventory } from "../api/hooks";

interface Props {
  opened: boolean;
  onClose: () => void;
  departmentId: number;
}

export function RequestStockModal({ opened, onClose, departmentId }: Props) {
  const { data: inventory } = useInventory(departmentId);
  const [itemId, setItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number | string>(1);

  const createReq = useCreateStockRequest();

  const items = (inventory || []).map((i) => ({
    value: String(i.id),
    label: `${i.name} (Available: ${i.quantity} ${i.unit || "units"})`,
  }));

  const handleSubmit = async () => {
    if (!itemId || Number(quantity) <= 0) return;
    try {
      await createReq.mutateAsync({
        department: departmentId,
        item: Number(itemId),
        quantity: Number(quantity),
      });
      notifications.show({
        title: "Stock Request Submitted",
        message: "Your request is awaiting HOD approval.",
        color: "teal",
      });
      setItemId(null);
      setQuantity(1);
      onClose();
    } catch (e) {
      notifications.show({
        title: "Request Failed",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Request Stock"
      subtitle="Submit an item requisition for official academic or lab use"
      onSubmit={handleSubmit}
      submitting={createReq.isPending}
      disabled={!itemId || Number(quantity) <= 0}
    >
      <Stack gap="sm">
        <Select
          label="Item"
          placeholder="Select an item from inventory"
          required
          data={items}
          value={itemId}
          onChange={setItemId}
          searchable
        />
        <NumberInput
          label="Requested Quantity"
          required
          min={1}
          value={quantity}
          onChange={setQuantity}
        />
      </Stack>
    </FormModal>
  );
}
