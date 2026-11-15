import { useState } from "react";
import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Stack,
  Text,
  Textarea,
  ThemeIcon,
  Title,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheck,
  FaBan,
  FaArchive,
  FaUserGraduate,
  FaChalkboardTeacher,
  FaUserTie,
  FaInfoCircle,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useArchiveUser, useUpdateUserStatus } from "../api/hooks";
import type { AdminUser, UserStatus } from "../api/types";

export function UserDetailsDrawer({
  user,
  opened,
  onClose,
}: {
  user: AdminUser | null;
  opened: boolean;
  onClose: () => void;
}) {
  const { session } = useAuth();
  const updateStatus = useUpdateUserStatus();
  const archiveUser = useArchiveUser();

  const [reason, setReason] = useState("");
  const [actionTarget, setActionTarget] = useState<UserStatus | "archive" | null>(
    null,
  );

  if (!user) return null;

  const isSelf = session?.user?.id === user.id;

  const handleApplyTransition = () => {
    if (!reason.trim()) {
      notifications.show({
        color: "red",
        title: "Reason Required",
        message: "An audit reason is required for lifecycle state changes.",
      });
      return;
    }

    if (actionTarget === "archive") {
      archiveUser.mutate(
        { user_id: user.id, reason: reason.trim() },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Account Archived",
              message: `${user.username} has been placed in reversible archival.`,
            });
            setReason("");
            setActionTarget(null);
            onClose();
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Archival Failed",
              message: errorMessage(err),
            });
          },
        },
      );
    } else if (actionTarget) {
      updateStatus.mutate(
        {
          id: user.id,
          payload: { new_status: actionTarget, reason: reason.trim() },
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Status Updated",
              message: `${user.username} status set to ${actionTarget}.`,
            });
            setReason("");
            setActionTarget(null);
            onClose();
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Status Update Failed",
              message: errorMessage(err),
            });
          },
        },
      );
    }
  };

  const getKindIcon = () => {
    switch (user.kind) {
      case "student":
        return <FaUserGraduate size={18} />;
      case "faculty":
        return <FaChalkboardTeacher size={18} />;
      case "staff":
        return <FaUserTie size={18} />;
    }
  };

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="md"
      title={
        <Group gap="xs">
          <ThemeIcon variant="light" color="blue" size="lg">
            {getKindIcon()}
          </ThemeIcon>
          <div>
            <Title order={4}>{user.profile?.display_name || user.username}</Title>
            <Text size="xs" c="dimmed">
              {user.institute_id} · {user.kind.toUpperCase()}
            </Text>
          </div>
        </Group>
      }
    >
      <Stack gap="lg" mt="md">
        <div>
          <Text size="xs" fw={700} c="dimmed" tt="uppercase">
            Account Status
          </Text>
          <Group mt={4} justify="space-between">
            <StatusBadge status={user.status} />
            <Text size="xs" c="dimmed">
              Joined: {user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
            </Text>
          </Group>
        </div>

        <Divider />

        <div>
          <Text size="xs" fw={700} c="dimmed" tt="uppercase" mb="xs">
            Profile Details
          </Text>
          <Stack gap="xs">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Email:</Text>
              <Text size="sm" fw={500}>{user.email}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Department:</Text>
              <Text size="sm" fw={500}>{user.profile?.department || "—"}</Text>
            </Group>
            {user.profile?.discipline && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Discipline:</Text>
                <Text size="sm" fw={500}>{user.profile.discipline}</Text>
              </Group>
            )}
            {user.profile?.programme && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Programme:</Text>
                <Text size="sm" fw={500}>{user.profile.programme}</Text>
              </Group>
            )}
            {user.profile?.batch_year && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Batch Year:</Text>
                <Text size="sm" fw={500}>{user.profile.batch_year}</Text>
              </Group>
            )}
            {user.profile?.employee_id && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Employee ID:</Text>
                <Text size="sm" fw={500}>{user.profile.employee_id}</Text>
              </Group>
            )}
            {user.profile?.contact_number && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Contact:</Text>
                <Text size="sm" fw={500}>{user.profile.contact_number}</Text>
              </Group>
            )}
          </Stack>
        </div>

        <Divider />

        <div>
          <Text size="xs" fw={700} c="dimmed" tt="uppercase" mb="xs">
            Lifecycle Actions
          </Text>

          {isSelf ? (
            <Alert icon={<FaInfoCircle size={14} />} color="blue" variant="light">
              Security Policy (BR-SA-028): You cannot modify or change the status
              of your own account.
            </Alert>
          ) : (
            <Stack gap="sm">
              <Group grow>
                {user.status !== "active" && (
                  <Button
                    size="xs"
                    color="teal"
                    variant="light"
                    leftSection={<FaCheck size={12} />}
                    onClick={() => setActionTarget("active")}
                  >
                    Activate
                  </Button>
                )}
                {user.status !== "deactivated" && (
                  <Button
                    size="xs"
                    color="orange"
                    variant="light"
                    leftSection={<FaBan size={12} />}
                    onClick={() => setActionTarget("deactivated")}
                  >
                    Deactivate
                  </Button>
                )}
                {user.status !== "archived" && (
                  <Button
                    size="xs"
                    color="gray"
                    variant="light"
                    leftSection={<FaArchive size={12} />}
                    onClick={() => setActionTarget("archive")}
                  >
                    Archive
                  </Button>
                )}
              </Group>

              {actionTarget && (
                <Stack gap="xs" p="sm" style={{ background: "#f8f9fa", borderRadius: 6 }}>
                  <Text size="xs" fw={600}>
                    Confirm {actionTarget.toUpperCase()} for {user.username}
                  </Text>
                  <Textarea
                    placeholder="Audit reason for status change (required)..."
                    value={reason}
                    onChange={(e) => setReason(e.currentTarget.value)}
                    size="xs"
                    rows={2}
                  />
                  <Group justify="flex-end" gap="xs">
                    <Button
                      size="xs"
                      variant="subtle"
                      onClick={() => {
                        setActionTarget(null);
                        setReason("");
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      size="xs"
                      color={actionTarget === "archive" ? "gray" : "blue"}
                      loading={updateStatus.isPending || archiveUser.isPending}
                      onClick={handleApplyTransition}
                    >
                      Confirm Transition
                    </Button>
                  </Group>
                </Stack>
              )}
            </Stack>
          )}
        </div>
      </Stack>
    </Drawer>
  );
}
