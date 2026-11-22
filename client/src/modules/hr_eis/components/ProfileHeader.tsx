import { Avatar, Badge, Card, Group, Stack, Text, Title } from "@mantine/core";
import { FaUserTie, FaEnvelope, FaIdCard, FaBuilding, FaCalendarAlt } from "react-icons/fa";
import type { EmployeeProfile } from "../api/types";

interface ProfileHeaderProps {
  profile: EmployeeProfile;
}

const DESIGNATION_LABELS: Record<string, string> = {
  PROFESSOR: "Professor",
  ASSOC_PROF: "Associate Professor",
  ASST_PROF: "Assistant Professor",
  STAFF: "Technical / Administrative Staff",
};

const DEPARTMENT_LABELS: Record<string, string> = {
  CSE: "Computer Science & Engineering",
  ECE: "Electronics & Communication Engineering",
  ME: "Mechanical Engineering",
  DESIGN: "Design",
  NS: "Natural Sciences",
};

export function ProfileHeader({ profile }: ProfileHeaderProps) {
  const designationLabel =
    DESIGNATION_LABELS[profile.designation] ?? profile.designation;
  const departmentLabel =
    DEPARTMENT_LABELS[profile.department] ?? profile.department;

  return (
    <Card withBorder padding="xl" radius="md" shadow="sm">
      <Group align="flex-start" justify="space-between">
        <Group align="center" gap="lg">
          <Avatar size={80} radius="xl" color="blue">
            <FaUserTie size={40} />
          </Avatar>
          <Stack gap={4}>
            <Group gap="xs">
              <Title order={3}>{profile.username}</Title>
              <Badge color="blue" variant="filled" size="sm">
                {designationLabel}
              </Badge>
            </Group>
            <Group gap="md" c="dimmed">
              <Group gap={4}>
                <FaIdCard size={14} />
                <Text size="sm">PF: {profile.pf_number}</Text>
              </Group>
              <Group gap={4}>
                <FaBuilding size={14} />
                <Text size="sm">{departmentLabel}</Text>
              </Group>
              {profile.email && (
                <Group gap={4}>
                  <FaEnvelope size={14} />
                  <Text size="sm">{profile.email}</Text>
                </Group>
              )}
            </Group>
          </Stack>
        </Group>

        <Group gap={6} c="dimmed">
          <FaCalendarAlt size={14} />
          <Text size="xs">
            Joined: {new Date(profile.date_of_joining).toLocaleDateString()}
          </Text>
        </Group>
      </Group>

      {profile.about_me && (
        <Stack mt="md" pt="md" style={{ borderTop: "1px solid #eee" }}>
          <Text size="sm" fw={500} c="dimmed">
            About
          </Text>
          <Text size="sm">{profile.about_me}</Text>
        </Stack>
      )}
    </Card>
  );
}
