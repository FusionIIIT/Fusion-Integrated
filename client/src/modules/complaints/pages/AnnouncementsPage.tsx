import {
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import dayjs from "dayjs";
import { useState } from "react";
import { FaBullhorn, FaPlus, FaThumbtack } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { useAnnouncements, useCategories, usePublishAnnouncement } from "../api/hooks";

export function AnnouncementsPage() {
  const { can, session } = useAuth();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);

  // Form state
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [pinned, setPinned] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const canPublish =
    can("complaints.announcement.publish") || session?.active_role === "admin";

  const { data: announcements, isLoading } = useAnnouncements(
    selectedCategory ? Number(selectedCategory) : null
  );
  const { data: categories } = useCategories();
  const publishMutation = usePublishAnnouncement();

  const handlePublish = async () => {
    if (!title.trim() || !content.trim()) {
      setErrorMsg("Title and content are mandatory.");
      return;
    }
    setErrorMsg("");
    try {
      await publishMutation.mutateAsync({
        title: title.trim(),
        content: content.trim(),
        category_id: categoryId ? Number(categoryId) : null,
        pinned,
      });
      closeModal();
      setTitle("");
      setContent("");
      setCategoryId(null);
      setPinned(false);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Failed to publish announcement.");
    }
  };

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>Complaints Notices & Announcements</Title>
            <Text c="dimmed" size="sm">
              Institutional maintenance bulletins, outages, and service advisories.
            </Text>
          </div>
          {canPublish && (
            <Button leftSection={<FaPlus />} onClick={openModal}>
              New Announcement
            </Button>
          )}
        </Group>

        <Group>
          <Select
            placeholder="Filter by Category"
            clearable
            value={selectedCategory}
            onChange={setSelectedCategory}
            data={categories?.map((cat) => ({ value: String(cat.id), label: cat.name })) || []}
          />
        </Group>

        {isLoading ? (
          <Stack align="center" py="xl">
            <Loader size="md" />
          </Stack>
        ) : !announcements || announcements.length === 0 ? (
          <Card withBorder p="xl" radius="md">
            <Stack align="center">
              <FaBullhorn size={32} color="#aaa" />
              <Text c="dimmed">No announcements currently published.</Text>
            </Stack>
          </Card>
        ) : (
          <Stack gap="md">
            {announcements.map((item) => (
              <Card
                key={item.id}
                withBorder
                radius="md"
                p="md"
                style={item.pinned ? { borderColor: "#f08c00", borderWidth: 2 } : undefined}
              >
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    {item.pinned && (
                      <Badge color="orange" leftSection={<FaThumbtack size={10} />}>
                        Pinned
                      </Badge>
                    )}
                    {item.category_name && (
                      <Badge variant="light" color="blue">
                        {item.category_name}
                      </Badge>
                    )}
                    <Title order={4}>{item.title}</Title>
                  </Group>
                  <Text size="xs" c="dimmed">
                    {dayjs(item.created_at).format("DD MMM YYYY, hh:mm A")}
                  </Text>
                </Group>

                <Text size="sm" style={{ whiteSpace: "pre-wrap" }} c="gray.8">
                  {item.content}
                </Text>

                <Text size="xs" c="dimmed" mt="sm">
                  Published by: {item.author_name}
                </Text>
              </Card>
            ))}
          </Stack>
        )}

        {/* Modal: Publish Announcement */}
        <Modal opened={modalOpened} onClose={closeModal} title="Publish Announcement" size="lg">
          <Stack gap="md">
            {errorMsg && (
              <Text c="red" size="sm">
                {errorMsg}
              </Text>
            )}

            <TextInput
              label="Title"
              placeholder="e.g. Scheduled Water Maintenance in Hall 3"
              required
              value={title}
              onChange={(e) => setTitle(e.currentTarget.value)}
            />

            <Select
              label="Specific Category (Optional)"
              placeholder="General notice or select category"
              clearable
              value={categoryId}
              onChange={setCategoryId}
              data={categories?.map((c) => ({ value: String(c.id), label: c.name })) || []}
            />

            <Textarea
              label="Announcement Content"
              placeholder="Write the notice details here..."
              required
              minRows={4}
              value={content}
              onChange={(e) => setContent(e.currentTarget.value)}
            />

            <Checkbox
              label="Pin this announcement to top of the bulletin"
              checked={pinned}
              onChange={(e) => setPinned(e.currentTarget.checked)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={closeModal}>
                Cancel
              </Button>
              <Button loading={publishMutation.isPending} onClick={handlePublish}>
                Publish
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}

export default AnnouncementsPage;

