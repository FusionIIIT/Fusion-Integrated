import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Grid,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus, FaThumbtack, FaBullhorn } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useHostels,
  useNotices,
  usePublishNotice,
} from "../api/hooks";

export default function NoticeBoardPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);

  const {
    data: notices,
    isPending,
    error,
  } = useNotices(selectedHostel ? Number(selectedHostel) : undefined);

  const publishMutation = usePublishNotice();

  // Publish Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [nHostelId, setNHostelId] = useState<string | null>(null);
  const [nTitle, setNTitle] = useState("");
  const [nCategory, setNCategory] = useState<string | null>("general");
  const [nBody, setNBody] = useState("");
  const [nPinned, setNPinned] = useState(false);
  const [nRole, setNRole] = useState("caretaker");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handlePublish = async () => {
    if (!nTitle || !nBody) return;
    await publishMutation.mutateAsync({
      hostel: nHostelId ? Number(nHostelId) : null,
      title: nTitle,
      body: nBody,
      category: nCategory || "general",
      is_pinned: nPinned,
      published_by_role: nRole,
    });
    setModalOpen(false);
    setNTitle("");
    setNBody("");
    setNPinned(false);
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "emergency":
        return "red";
      case "discipline":
        return "orange";
      case "maintenance":
        return "yellow";
      case "event":
        return "teal";
      default:
        return "blue";
    }
  };

  // Sort pinned notices first
  const sortedNotices = [...(notices || [])].sort((a, b) => {
    if (a.is_pinned === b.is_pinned) {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    }
    return a.is_pinned ? -1 : 1;
  });

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Notice Board"
          subtitle="Official announcements, mess & maintenance advisories, and administrative directives"
          action={
            <Button
              leftSection={<FaPlus />}
              onClick={() => setModalOpen(true)}
            >
              Publish Notice
            </Button>
          }
        />

        <Group justify="space-between">
          <Select
            placeholder="Filter by hostel"
            clearable
            value={selectedHostel}
            onChange={setSelectedHostel}
            data={[
              ...(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              })),
            ]}
            style={{ width: 280 }}
          />

          <Badge size="lg" variant="light" leftSection={<FaBullhorn />}>
            {sortedNotices.length} Published Notices
          </Badge>
        </Group>

        {isPending ? (
          <Text size="sm">Loading notices...</Text>
        ) : sortedNotices.length === 0 ? (
          <Card withBorder p="xl" radius="md">
            <Stack align="center" gap="xs">
              <FaBullhorn size={32} color="gray" />
              <Text fw={500}>No notices posted</Text>
              <Text size="xs" c="dimmed">
                No active announcements for this hostel selection.
              </Text>
            </Stack>
          </Card>
        ) : (
          <Grid>
            {sortedNotices.map((notice) => (
              <Grid.Col key={notice.id} span={{ base: 12, md: 6, lg: 4 }}>
                <Card
                  withBorder
                  radius="md"
                  p="md"
                  style={{
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    borderColor: notice.is_pinned ? "var(--mantine-color-blue-4)" : undefined,
                  }}
                >
                  <Stack gap="xs">
                    <Group justify="space-between" align="center">
                      <Badge color={getCategoryColor(notice.category)} size="sm">
                        {notice.category.toUpperCase()}
                      </Badge>
                      {notice.is_pinned && (
                        <Badge
                          color="blue"
                          variant="filled"
                          size="sm"
                          leftSection={<FaThumbtack size={10} />}
                        >
                          Pinned
                        </Badge>
                      )}
                    </Group>

                    <Text fw={600} size="md" lineClamp={2}>
                      {notice.title}
                    </Text>

                    <Text size="sm" c="dimmed" style={{ whiteSpace: "pre-line" }} lineClamp={5}>
                      {notice.body}
                    </Text>
                  </Stack>

                  <Stack gap={4} mt="md" pt="xs" style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}>
                    <Group justify="space-between">
                      <Text size="xs" fw={500} c="blue">
                        {notice.hostel_name ? notice.hostel_name : "All Hostels (Institute-wide)"}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {notice.published_by_role?.toUpperCase()}
                      </Text>
                    </Group>
                    <Text size="xs" c="dimmed">
                      {new Date(notice.created_at).toLocaleString()}
                    </Text>
                  </Stack>
                </Card>
              </Grid.Col>
            ))}
          </Grid>
        )}

        {/* Modal: Publish Notice */}
        <Modal
          opened={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Publish Official Hostel Notice"
          size="lg"
        >
          <Stack gap="sm">
            <Group grow>
              <Select
                label="Target Hostel Scope"
                placeholder="Leave empty for all hostels (institute-wide)"
                clearable
                data={(hostels || []).map((h) => ({
                  value: String(h.id),
                  label: `${h.name} (${h.code})`,
                }))}
                value={nHostelId}
                onChange={setNHostelId}
              />
              <Select
                label="Notice Category"
                required
                data={[
                  { value: "general", label: "General Information" },
                  { value: "maintenance", label: "Maintenance & Repairs" },
                  { value: "discipline", label: "Discipline & Code of Conduct" },
                  { value: "event", label: "Hostel Events & Gatherings" },
                  { value: "emergency", label: "Emergency / Urgent Alert" },
                ]}
                value={nCategory}
                onChange={setNCategory}
              />
            </Group>

            <TextInput
              label="Notice Subject / Headline"
              required
              placeholder="e.g. Scheduled Water Pipeline Maintenance on Saturday"
              value={nTitle}
              onChange={(e) => setNTitle(e.target.value)}
            />

            <Textarea
              label="Notice Body & Instructions"
              required
              minRows={5}
              placeholder="Enter full announcement details, timings, and instructions for residents..."
              value={nBody}
              onChange={(e) => setNBody(e.target.value)}
            />

            <Group justify="space-between" mt="xs">
              <Select
                label="Publishing Authority"
                data={[
                  { value: "caretaker", label: "Hostel Caretaker" },
                  { value: "warden", label: "Hostel Warden" },
                  { value: "admin", label: "Hostel Super Admin" },
                ]}
                value={nRole}
                onChange={(v) => setNRole(v || "caretaker")}
                style={{ width: 200 }}
              />

              <Checkbox
                label="Pin notice to top of board"
                checked={nPinned}
                onChange={(e) => setNPinned(e.currentTarget.checked)}
                mt="xl"
              />
            </Group>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={publishMutation.isPending}
                disabled={!nTitle || !nBody}
                onClick={handlePublish}
              >
                Publish Notice
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
