import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaPlus, FaTrash } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAnnouncements,
  useDeleteAnnouncement,
  useDepartments,
} from "../api/hooks";
import { NewAnnouncementModal } from "../components/NewAnnouncementModal";

export default function AnnouncementsPage() {
  const { can } = useAuth();
  const { data: depts } = useDepartments();
  const defaultDept = depts?.[0];
  const deptId = defaultDept?.id;

  const { data: announcements, isPending, error } = useAnnouncements(deptId);
  const deleteAnn = useDeleteAnnouncement();

  const [writing, setWriting] = useState(false);
  const [filterAudience, setFilterAudience] = useState<string>("all");

  const canPublish = can("department.announcement.publish");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = (announcements || []).filter((a) => {
    if (filterAudience === "all") return true;
    return a.role_target === filterAudience;
  });

  const handleDelete = async (id: number) => {
    try {
      await deleteAnn.mutateAsync(id);
      notifications.show({
        title: "Announcement removed",
        message: "The announcement has been deleted.",
        color: "teal",
      });
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to delete announcement.",
        color: "red",
      });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Department Announcements"
        subtitle="Notices, academic updates, and official announcements"
        action={
          canPublish && deptId && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setWriting(true)}
            >
              Publish Notice
            </Button>
          )
        }
      />

      <Group justify="space-between" mb="md">
        <Select
          label="Filter by Audience"
          size="xs"
          data={[
            { value: "all", label: "All notices" },
            { value: "student", label: "Students only" },
            { value: "faculty", label: "Faculty only" },
          ]}
          value={filterAudience}
          onChange={(v) => setFilterAudience(v || "all")}
          style={{ width: 180 }}
        />
        <Text size="xs" c="dimmed" mt="auto">
          Showing {rows.length} notice(s)
        </Text>
      </Group>

      {isPending && <Text c="dimmed">Loading notices…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={8}>
            <FaBullhorn size={28} color="var(--mantine-color-gray-5)" />
            <Title order={4}>No announcements found</Title>
            <Text size="sm" c="dimmed">
              No notices match your current selection.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((a) => (
          <Card key={a.id} padding="lg" withBorder>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={6} style={{ flex: 1 }}>
                <Group gap="xs" wrap="wrap">
                  <Text fw={700} size="md">
                    {a.title}
                  </Text>
                  {a.role_target && (
                    <Badge variant="light" size="xs" color="indigo">
                      {a.role_target}
                    </Badge>
                  )}
                  {a.academic_year && (
                    <Badge variant="outline" size="xs">
                      {a.academic_year}
                    </Badge>
                  )}
                  {a.programme && (
                    <Badge variant="dot" size="xs" color="teal">
                      {a.programme}
                    </Badge>
                  )}
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {a.body}
                </Text>
                <Text size="xs" c="dimmed">
                  Posted by User #{a.created_by_user_id} ·{" "}
                  {new Date(a.created_at).toLocaleString()}
                </Text>
              </Stack>

              {canPublish && (
                <ActionIcon
                  color="red"
                  variant="subtle"
                  title="Delete Notice"
                  loading={deleteAnn.isPending}
                  onClick={() => handleDelete(a.id)}
                >
                  <FaTrash size={14} />
                </ActionIcon>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      {deptId && (
        <NewAnnouncementModal
          opened={writing}
          onClose={() => setWriting(false)}
          departmentId={deptId}
        />
      )}
    </Container>
  );
}
