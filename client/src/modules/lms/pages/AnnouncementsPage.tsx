import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
} from "@mantine/core";
import { FaBullhorn, FaCalendarAlt, FaSearch, FaThumbtack } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAllAnnouncements } from "../api/hooks";

const ROLE_COLORS: Record<string, string> = {
  faculty: "blue",
  ta: "violet",
  student: "teal",
  observer: "gray",
};

export default function AnnouncementsPage() {
  const navigate = useNavigate();
  const { data: announcements, isPending, error } = useAllAnnouncements();

  const [search, setSearch] = useState("");

  if (error) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const list = announcements ?? [];

  const filtered = list.filter((a) => {
    return (
      a.title.toLowerCase().includes(search.toLowerCase()) ||
      a.content.toLowerCase().includes(search.toLowerCase()) ||
      (a.posted_by_name && a.posted_by_name.toLowerCase().includes(search.toLowerCase()))
    );
  });

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Course Announcements"
        subtitle="Recent notices and broadcasts across all enrolled course workspaces"
      />

      <Card withBorder mb="lg" padding="md">
        <TextInput
          placeholder="Search announcements by title, keyword, or author..."
          leftSection={<FaSearch size={14} color="var(--mantine-color-gray-5)" />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
        />
      </Card>

      {isPending && <Text c="dimmed">Loading announcements...</Text>}

      {!isPending && filtered.length === 0 && (
        <Card padding="xl" withBorder style={{ textAlign: "center" }}>
          <Stack align="center" gap="xs">
            <ThemeIcon size={46} radius="xl" color="gray" variant="light">
              <FaBullhorn size={22} />
            </ThemeIcon>
            <Text fw={600} size="md">
              No announcements found
            </Text>
            <Text c="dimmed" size="xs">
              No notifications posted yet.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {filtered.map((a) => (
          <Card
            key={a.id}
            withBorder
            padding="lg"
            radius="md"
            style={
              a.is_pinned
                ? {
                    borderLeft: "4px solid var(--mantine-color-indigo-6)",
                    background: "var(--mantine-color-indigo-0)",
                  }
                : undefined
            }
          >
            <Group justify="space-between" align="flex-start" mb="xs">
              <Group gap="xs">
                {a.is_pinned && (
                  <Badge color="indigo" variant="filled" size="sm" leftSection={<FaThumbtack size={10} />}>
                    PINNED
                  </Badge>
                )}
                <Text fw={700} size="md">
                  {a.title}
                </Text>
              </Group>
              <Text size="xs" c="dimmed">
                <FaCalendarAlt style={{ verticalAlign: "middle", marginRight: 4 }} />
                {new Date(a.created_at).toLocaleString()}
              </Text>
            </Group>

            <Text size="sm" style={{ whiteSpace: "pre-wrap" }} mb="md">
              {a.content}
            </Text>

            <Divider mb="xs" />
            <Group justify="space-between">
              <Text size="xs" c="dimmed">
                Posted by: <strong>{a.posted_by_name || `User #${a.posted_by_user_id}`}</strong>
              </Text>
              <Group gap="xs">
                <Badge size="xs" color={ROLE_COLORS[a.posted_by_role] ?? "gray"} variant="light">
                  {a.posted_by_role.toUpperCase()}
                </Badge>
                <Button
                  size="xs"
                  variant="subtle"
                  color="indigo"
                  onClick={() => navigate(`/lms/courses?courseId=${a.course}`)}
                >
                  Go to Course Workspace &rarr;
                </Button>
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
