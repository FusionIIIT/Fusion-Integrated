import { Stack } from "@mantine/core";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useStock } from "../api/hooks";
import type { StockItem } from "../api/types";

export default function InventoryPage() {
  const { data: stocks = [], isLoading } = useStock();

  const columns: Column<StockItem>[] = [
    { key: "item_code", header: "Item Code" },
    { key: "item_name", header: "Item Name" },
    {
      key: "quantity_on_hand",
      header: "On Hand",
      align: "right",
      render: (r) => r.quantity_on_hand.toLocaleString(),
    },
    {
      key: "quantity_reserved",
      header: "Reserved",
      align: "right",
      render: (r) => r.quantity_reserved.toLocaleString(),
    },
    {
      key: "available_quantity",
      header: "Available Balance",
      align: "right",
      render: (r) => (
        <span style={{ fontWeight: 600, color: r.available_quantity > 0 ? "inherit" : "red" }}>
          {r.available_quantity.toLocaleString()}
        </span>
      ),
    },
    {
      key: "reorder_level",
      header: "Reorder Threshold",
      align: "right",
      render: (r) => r.reorder_level.toLocaleString(),
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Central Stores Inventory"
        subtitle="Current stock levels, reserved quantities, and warehouse availability"
      />
      <DataTable
        rows={stocks}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No stock inventory items found",
          description: "Inventory records are created as items are catalogued and received into the central store.",
        }}
      />
    </Stack>
  );
}
