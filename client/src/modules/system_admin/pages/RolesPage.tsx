import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  Modal,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExchangeAlt, FaIdBadge, FaPlus, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useRevokeRole, useRoles } from "../api/hooks";
import type { RoleAssignment, RoleDefinition } from "../api/types";
import { RoleAssignModal } from "../components/RoleAssignModal";
import { RoleHandoverModal } from "../components/RoleHandoverModal";

export default function RolesPage() {
  const { data, isPending, error } = useRoles();
  const revokeRole = useRevokeRole();

  const [assigning, setAssigning] = useState(false);
  const [selectedForHandover, setSelectedForHandover] =
    useState<RoleAssignment | null>(null);
  const [revokingAssignment, setRevokingAssignment] =
    useState<RoleAssignment | null>(null);
  const [revokeReason, setRevokeReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  // Parse server response which could be an object { definitions, assignments } or Page<RoleAssignment> or array
  let assignments: RoleAssignment[] = [];
  let definitions: RoleDefinition[] = [];

  if (data && typeof data === "object") {
    if ("assignments" in data && Array.isArray((data as any).assignments)) {
      assignments = (data as any).assignments;
    } else if ("results" in data && Array.isArray((data as any).results)) {
      assignments = (data as any).results;
    } else if (Array.isArray(data)) {
      assignments = data;
    }

    if ("definitions" in data && Array.isArray((data as any).definitions)) {
      definitions = (data as any).definitions;
    }
  }

  const handleConfirmRevocation = () => {
    if (!revokingAssignment || !revokeReason.trim()) {
      notifications.show({
        color: "red",
        title: "Reason Required",
        message: "A revocation justification is required.",
      });
      return;
    }

    revokeRole.mutate(
      {
        assignment_id: revokingAssignment.id,
        is_emergency: false,
        effective_date: new Date().toISOString().split("T")[0],
        reason: revokeReason.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Role Revoked",
            message: `Role assignment #${revokingAssignment.id} revoked.`,
          });
          setRevokingAssignment(null);
          setRevokeReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Revocation Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Roles & Authority"
        subtitle="Manage administrative designations, time-bound tenures, and atomic handovers"
        action={
          <Button
            leftSection={<FaPlus size={12} />}
            onClick={() => setAssigning(true)}
          >
            Assign Role
          </Button>
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<RoleAssignment>
          rows={assignments}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "role_id",
              header: "Designation / Role",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.role_id}</Text>
                  <Text size="xs" c="dimmed">
                    Assignment #{r.id}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "user_id",
              header: "User ID",
              render: (r) => (
                <Badge variant="light" size="sm">
                  User #{r.user_id}
                </Badge>
              ),
            },
            {
              key: "scope",
              header: "Scope",
              render: (r) => <Text size="sm">{r.scope || "Institutional"}</Text>,
            },
            {
              key: "tenure",
              header: "Tenure Period",
              render: (r) => (
                <Text size="xs">
                  {r.start_date} {r.end_date ? `to ${r.end_date}` : "(Ongoing)"}
                </Text>
              ),
            },
            {
              key: "state",
              header: "State",
              render: (r) => <StatusBadge status={r.state} />,
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) =>
                r.state === "active" ? (
                  <Group gap="xs" justify="flex-end">
                    <Button
                      size="xs"
                      variant="light"
                      color="blue"
                      leftSection={<FaExchangeAlt size={10} />}
                      onClick={() => setSelectedForHandover(r)}
                    >
                      Handover
                    </Button>
                    <Button
                      size="xs"
                      variant="subtle"
                      color="red"
                      leftSection={<FaTimes size={10} />}
                      onClick={() => setRevokingAssignment(r)}
                    >
                      Revoke
                    </Button>
                  </Group>
                ) : (
                  <Text size="xs" c="dimmed">
                    —
                  </Text>
                ),
            },
          ]}
          empty={{
            icon: FaIdBadge,
            title: "No Role Assignments",
            description: "No administrative or functional role delegations found.",
          }}
        />
      </Card>

      <RoleAssignModal
        opened={assigning}
        onClose={() => setAssigning(false)}
        definitions={definitions}
      />

      <RoleHandoverModal
        assignment={selectedForHandover}
        opened={Boolean(selectedForHandover)}
        onClose={() => setSelectedForHandover(null)}
      />

      <Modal
        opened={Boolean(revokingAssignment)}
        onClose={() => setRevokingAssignment(null)}
        title="Confirm Role Revocation"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to revoke role{" "}
            <strong>{revokingAssignment?.role_id}</strong> from user #
            {revokingAssignment?.user_id}?
          </Text>

          <Textarea
            label="Revocation Justification"
            placeholder="Reason for revoking authority..."
            value={revokeReason}
            onChange={(e) => setRevokeReason(e.currentTarget.value)}
            required
            rows={3}
          />

          <Group justify="flex-end">
            <Button
              variant="subtle"
              onClick={() => setRevokingAssignment(null)}
            >
              Cancel
            </Button>
            <Button
              color="red"
              loading={revokeRole.isPending}
              onClick={handleConfirmRevocation}
            >
              Confirm Revoke
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
