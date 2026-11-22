import {
  ActionIcon,
  Button,
  Card,
  Grid,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useState } from "react";
import { FaPlus, FaTrash } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateIndent, useItems } from "../api/hooks";

interface ItemRow {
  item_master_id: number;
  quantity_requested: number;
  estimated_unit_cost: string;
  specifications: string;
}

export default function IndentCreatePage() {
  const navigate = useNavigate();
  const { data: items = [] } = useItems();
  const createIndent = useCreateIndent();

  const [departmentCode, setDepartmentCode] = useState("CSE");
  const [title, setTitle] = useState("");
  const [purpose, setPurpose] = useState("");
  const [priority, setPriority] = useState<string>("STANDARD");
  const [lines, setLines] = useState<ItemRow[]>([
    { item_master_id: 1, quantity_requested: 1, estimated_unit_cost: "1000.00", specifications: "" },
  ]);
  const [error, setError] = useState<string | null>(null);

  const addItem = () => {
    setLines((prev) => [
      ...prev,
      { item_master_id: items[0]?.id ?? 1, quantity_requested: 1, estimated_unit_cost: "500.00", specifications: "" },
    ]);
  };

  const removeItem = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateLine = (idx: number, patch: Partial<ItemRow>) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!title.trim() || !purpose.trim()) {
      setError("Title and justification purpose are required.");
      return;
    }
    if (lines.length === 0) {
      setError("Please add at least one line item.");
      return;
    }

    try {
      await createIndent.mutateAsync({
        department_code: departmentCode,
        title,
        purpose,
        priority,
        items: lines,
      });
      navigate("/psm/indents");
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to create indent";
      setError(msg);
    }
  };

  const itemOptions = items.map((i) => ({ value: String(i.id), label: `${i.item_code} - ${i.name}` }));

  return (
    <Stack gap="lg">
      <PageHeader
        title="Raise Purchase Indent"
        subtitle="Initiate a procurement request adhering to institutional threshold guidelines"
      />
      <form onSubmit={handleSubmit}>
        <Card withBorder padding="lg" radius="md">
          <Stack gap="md">
            {error && (
              <Text c="red" size="sm" fw={500}>
                {error}
              </Text>
            )}

            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <TextInput
                  label="Indent Title"
                  placeholder="e.g. Lab Consumables Q4"
                  value={title}
                  onChange={(e) => setTitle(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 3 }}>
                <Select
                  label="Department"
                  value={departmentCode}
                  onChange={(val) => setDepartmentCode(val ?? "CSE")}
                  data={[
                    { value: "CSE", label: "Computer Science & Engineering" },
                    { value: "ECE", label: "Electronics & Communication" },
                    { value: "ME", label: "Mechanical Engineering" },
                    { value: "NS", label: "Natural Sciences" },
                  ]}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 3 }}>
                <Select
                  label="Priority"
                  value={priority}
                  onChange={(val) => setPriority(val ?? "STANDARD")}
                  data={[
                    { value: "LOW", label: "Low Priority" },
                    { value: "STANDARD", label: "Standard" },
                    { value: "URGENT", label: "Urgent" },
                  ]}
                />
              </Grid.Col>
            </Grid>

            <Textarea
              label="Purpose / Justification"
              placeholder="State academic or research necessity"
              value={purpose}
              onChange={(e) => setPurpose(e.currentTarget.value)}
              required
              rows={3}
            />

            <Text fw={600} size="sm" mt="md">
              Line Items
            </Text>
            {lines.map((line, idx) => (
              <Group key={idx} align="flex-end" grow>
                <Select
                  label={idx === 0 ? "Catalog Item" : undefined}
                  data={itemOptions.length > 0 ? itemOptions : [{ value: "1", label: "General Store Item" }]}
                  value={String(line.item_master_id)}
                  onChange={(v) => updateLine(idx, { item_master_id: Number(v) })}
                />
                <NumberInput
                  label={idx === 0 ? "Quantity" : undefined}
                  min={1}
                  value={line.quantity_requested}
                  onChange={(v) => updateLine(idx, { quantity_requested: Number(v) || 1 })}
                />
                <TextInput
                  label={idx === 0 ? "Estimated Unit Cost (₹)" : undefined}
                  value={line.estimated_unit_cost}
                  onChange={(e) => updateLine(idx, { estimated_unit_cost: e.currentTarget.value })}
                />
                <TextInput
                  label={idx === 0 ? "Specifications" : undefined}
                  placeholder="Optional specs"
                  value={line.specifications}
                  onChange={(e) => updateLine(idx, { specifications: e.currentTarget.value })}
                />
                {lines.length > 1 && (
                  <ActionIcon color="red" variant="subtle" onClick={() => removeItem(idx)} mb={4}>
                    <FaTrash size={14} />
                  </ActionIcon>
                )}
              </Group>
            ))}

            <Group justify="space-between" mt="md">
              <Button variant="default" size="sm" leftSection={<FaPlus size={12} />} onClick={addItem}>
                Add Item Line
              </Button>
              <Group>
                <Button variant="subtle" color="gray" onClick={() => navigate("/psm/indents")}>
                  Cancel
                </Button>
                <Button type="submit" loading={createIndent.isPending}>
                  Create Indent
                </Button>
              </Group>
            </Group>
          </Stack>
        </Card>
      </form>
    </Stack>
  );
}
