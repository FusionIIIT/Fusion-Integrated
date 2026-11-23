import { useEffect, useState } from "react";
import { Badge, Button, Container, Modal, NumberInput, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";

import { http, errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import type { InventoryItem } from "../types";

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Civil");
  const [stock, setStock] = useState<number | string>(10);
  const [unit, setUnit] = useState("pcs");
  const [price, setPrice] = useState("0.00");
  const [saving, setSaving] = useState(false);

  const fetchItems = () => {
    setLoading(true);
    http
      .get("/iwd/inventory/")
      .then((res) => {
        setItems(res.data.results || res.data);
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await http.post("/iwd/inventory/", {
        name,
        category,
        stock_quantity: Number(stock),
        unit,
        unit_price: price,
      });
      notifications.show({ color: "teal", title: "Item Added", message: `Stock for ${name} created.` });
      setModalOpen(false);
      setName("");
      fetchItems();
    } catch (err) {
      notifications.show({ color: "red", title: "Creation Failed", message: errorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  if (error) {
    return <Container size="xl"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Inventory & Stock"
        subtitle="Manage maintenance supplies and track material stock levels"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setModalOpen(true)}>
            Add Inventory Item
          </Button>
        }
      />

      <DataTable<InventoryItem>
        rows={items}
        loading={loading}
        rowKey={(it) => it.id}
        empty={{ title: "No inventory items", description: "Add maintenance parts and supplies above." }}
        columns={[
          {
            key: "id",
            header: "#",
            render: (it) => `#${it.id}`,
          },
          {
            key: "name",
            header: "Item Name",
            render: (it) => it.name,
          },
          {
            key: "category",
            header: "Category",
            render: (it) => it.category,
          },
          {
            key: "stock_quantity",
            header: "Available Quantity",
            render: (it) => (
              <Badge color={it.stock_quantity > 0 ? "teal" : "red"}>
                {it.stock_quantity} {it.unit}
              </Badge>
            ),
          },
          {
            key: "unit_price",
            header: "Unit Price (INR)",
            render: (it) => `Rs. ${it.unit_price}`,
          },
        ]}
      />

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="New Inventory Item">
        <Stack gap="md">
          <TextInput label="Item Name" required value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <TextInput label="Category" value={category} onChange={(e) => setCategory(e.currentTarget.value)} />
          <NumberInput label="Initial Stock" value={stock} onChange={setStock} min={0} />
          <TextInput label="Unit (e.g. pcs, kg, m)" value={unit} onChange={(e) => setUnit(e.currentTarget.value)} />
          <TextInput label="Unit Price (INR)" value={price} onChange={(e) => setPrice(e.currentTarget.value)} />
          <Button onClick={handleCreate} loading={saving} mt="md">
            Save Item
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
