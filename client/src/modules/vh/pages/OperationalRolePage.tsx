import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReassignRole } from "../api/hooks";

export default function OperationalRolePage() {
  const [roleName, setRoleName] = useState<"caretaker" | "incharge">("caretaker");
  const [newUserId, setNewUserId] = useState<number>(0);

  const reassignMutation = useReassignRole();

  const handleReassign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserId) {
      notifications.show({
        color: "red",
        message: "Valid User ID is required for operational assignment.",
      });
      return;
    }

    try {
      await reassignMutation.mutateAsync({
        role_name: roleName,
        new_user_id: newUserId,
      });
      notifications.show({
        color: "teal",
        message: `Role '${roleName}' successfully reassigned to User ${newUserId}. Operational records transferred.`,
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  return (
    <Container size="sm">
      <PageHeader
        title="Operational Role Management"
        subtitle="Designate Caretaker or VH In-Charge role holders. Pending records transfer automatically upon reassignment."
      />

      <Card padding="lg" withBorder component="form" onSubmit={handleReassign}>
        <Stack gap="md">
          <Select
            label="Hostel Operational Role"
            required
            data={[
              { value: "caretaker", label: "VH Caretaker (Operational Front Desk)" },
              { value: "incharge", label: "VH In-Charge (Faculty Supervisor)" },
            ]}
            value={roleName}
            onChange={(val) => setRoleName((val as "caretaker" | "incharge") || "caretaker")}
          />

          <NumberInput
            label="Designate Employee User ID"
            description="System user ID of the staff/faculty member assuming the role."
            required
            min={1}
            value={newUserId || ""}
            onChange={(val) => setNewUserId(Number(val) || 0)}
          />

          <Text size="xs" c="dimmed">
            Note: The previous role holder is immediately deactivated, and all ongoing/pending requisitions and workflows transfer to the new holder.
          </Text>

          <Group justify="flex-end" mt="md">
            <Button
              type="submit"
              color="blue"
              loading={reassignMutation.isPending}
              leftSection={<FaUserCheck size={14} />}
            >
              Reassign Role
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
