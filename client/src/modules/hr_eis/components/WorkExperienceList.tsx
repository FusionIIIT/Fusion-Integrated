import {
  ActionIcon,
  Badge,
  Card,
  Group,
  Stack,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBriefcase, FaCalendarAlt, FaTrash } from "react-icons/fa";
import { useDeleteWorkExperience } from "../api/hooks";
import type { WorkExperience } from "../api/types";

interface WorkExperienceListProps {
  experiences: WorkExperience[];
}

export function WorkExperienceList({ experiences }: WorkExperienceListProps) {
  const deleteMutation = useDeleteWorkExperience();

  const handleDelete = (id: number, org: string) => {
    if (!window.confirm(`Delete work experience at ${org}?`)) return;
    deleteMutation.mutate(id, {
      onSuccess: () => {
        notifications.show({
          title: "Experience Deleted",
          message: "The experience entry has been removed successfully.",
          color: "green",
        });
      },
      onError: (err) => {
        notifications.show({
          title: "Deletion Failed",
          message: err.message || "Failed to delete experience.",
          color: "red",
        });
      },
    });
  };

  if (!experiences || experiences.length === 0) {
    return (
      <Card withBorder padding="xl" radius="md">
        <Text c="dimmed" ta="center" size="sm">
          No professional work experiences recorded yet. Click "Add Experience" to record prior roles.
        </Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      {experiences.map((exp) => {
        const isOngoing = !exp.end_date;
        const startDateStr = new Date(exp.start_date).toLocaleDateString(
          undefined,
          { year: "numeric", month: "short" }
        );
        const endDateStr = isOngoing
          ? "Present"
          : new Date(exp.end_date!).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
            });

        return (
          <Card key={exp.id} withBorder padding="md" radius="md" shadow="xs">
            <Group justify="space-between" align="flex-start">
              <Group align="flex-start" gap="md">
                <ActionIcon variant="light" color="blue" size="lg" radius="md">
                  <FaBriefcase size={18} />
                </ActionIcon>
                <Stack gap={2}>
                  <Title order={5}>{exp.position}</Title>
                  <Text fw={500} size="sm" c="dimmed">
                    {exp.organization}
                  </Text>
                  <Group gap="xs" mt={4}>
                    <FaCalendarAlt size={12} color="#888" />
                    <Text size="xs" c="dimmed">
                      {startDateStr} – {endDateStr}
                    </Text>
                    {isOngoing && (
                      <Badge color="green" size="xs" variant="light">
                        Current Role
                      </Badge>
                    )}
                  </Group>
                  {exp.description && (
                    <Text size="sm" mt="xs" c="gray.7">
                      {exp.description}
                    </Text>
                  )}
                </Stack>
              </Group>

              <Tooltip label="Delete experience">
                <ActionIcon
                  color="red"
                  variant="subtle"
                  loading={
                    deleteMutation.isPending &&
                    deleteMutation.variables === exp.id
                  }
                  onClick={() => handleDelete(exp.id, exp.organization)}
                >
                  <FaTrash size={14} />
                </ActionIcon>
              </Tooltip>
            </Group>
          </Card>
        );
      })}
    </Stack>
  );
}
