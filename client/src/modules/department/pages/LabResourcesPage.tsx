import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaLaptopCode, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { useDepartments, useLabResources, useUpsertResource } from "../api/hooks";

export default function LabResourcesPage() {
  const { can } = useAuth();
  const { data: depts } = useDepartments();
  const defaultDept = depts?.[0];
  const deptId = defaultDept?.id;

  const { data: resources, isPending, error } = useLabResources(deptId);
  const upsert = useUpsertResource();

  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState<number | string>(1);

  const canManage = can("department.detail.update") || can("department.inventory.manage");

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  const handleAdd = async () => {
    if (!name.trim() || !deptId) return;
    try {
      await upsert.mutateAsync({
        department: deptId,
        name: name.trim(),
        description: description.trim(),
        quantity: Number(quantity),
      });
      notifications.show({
        title: "Resource Added",
        message: `${name} has been added to lab resources.`,
        color: "teal",
      });
      setName("");
      setDescription("");
      setQuantity(1);
      setModalOpen(false);
    } catch (e) {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Laboratory & Research Resources"
        subtitle="Department laboratories, computing clusters, instrumentation and hardware kits"
        action={
          canManage && deptId && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setModalOpen(true)}
            >
              Add Lab Resource
            </Button>
          )
        }
      />

      {isPending && <Text c="dimmed">Loading resources…</Text>}

      {!isPending && (resources || []).length === 0 && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={6}>
            <FaLaptopCode size={28} color="var(--mantine-color-gray-5)" />
            <Title order={4}>No lab resources registered</Title>
            <Text size="sm" c="dimmed">
              Use the button above to register lab equipment and facilities.
            </Text>
          </Stack>
        </Card>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        {(resources || []).map((r) => (
          <Card key={r.id} padding="lg" withBorder>
            <Stack gap="xs">
              <Group justify="space-between" align="flex-start">
                <Text fw={700} size="md">
                  {r.name}
                </Text>
                <Badge variant="light" color="blue">
                  Qty: {r.quantity}
                </Badge>
              </Group>

              {r.description && (
                <Text size="sm" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
                  {r.description}
                </Text>
              )}

              <Text size="xs" c="dimmed" mt="auto">
                Updated by User #{r.updated_by_user_id} ·{" "}
                {new Date(r.created_at).toLocaleDateString()}
              </Text>
            </Stack>
          </Card>
        ))}
      </SimpleGrid>

      <FormModal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Register Lab Resource"
        subtitle="Add computing clusters, oscilloscopes, FPGA boards, or workstations"
        onSubmit={handleAdd}
        submitting={upsert.isPending}
        disabled={!name.trim()}
      >
        <Stack gap="sm">
          <TextInput
            label="Resource Name"
            placeholder="e.g. NVIDIA A100 GPU Cluster / Digital Oscilloscope"
            required
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
          />
          <NumberInput
            label="Available Quantity"
            min={1}
            value={quantity}
            onChange={setQuantity}
          />
          <Textarea
            label="Specification / Description"
            placeholder="Technical details, lab location, usage guidelines..."
            minRows={3}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
