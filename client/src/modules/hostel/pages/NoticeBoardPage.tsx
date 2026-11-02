import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateNotice, useHostels, useNotices } from "../api/hooks";
import type { NoticeAudience } from "../api/types";

export default function NoticeBoardPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: noticesData, error: noticesError } = useNotices({ hostel_id: hostelId });

  const createNotice = useCreateNotice();
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // Form state
  const [noticeHostelId, setNoticeHostelId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [targetAudience, setTargetAudience] = useState<string>("all");
  const [expiresAt, setExpiresAt] = useState("");

  const handleCreate = async () => {
    try {
      await createNotice.mutateAsync({
        hostel: noticeHostelId ? Number(noticeHostelId) : null,
        title,
        content,
        target_audience: targetAudience as NoticeAudience,
        expires_at: expiresAt || null,
        is_active: true,
      });
      notifications.show({ title: "Success", message: "Notice published successfully", color: "green" });
      setCreateModalOpen(false);
      setTitle("");
      setContent("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to publish notice", color: "red" });
    }
  };

  if (noticesError) return <Container size="xl"><ErrorState error={noticesError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const notices = noticesData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Notice Board"
        subtitle="Digital bulletin board for hostel circulars, maintenance shutdowns, and mess notifications"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setCreateModalOpen(true)}>
            Publish Notice
          </Button>
        }
      />

      <Group mb="md">
        <Select
          placeholder="Filter by hostel"
          clearable
          data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
          value={selectedHostel}
          onChange={setSelectedHostel}
          style={{ width: 280 }}
        />
      </Group>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {notices.map((n) => (
          <Card key={n.id} withBorder shadow="sm" radius="md" p="lg">
            <Group justify="space-between" mb="xs">
              <Badge variant="filled" color="blue">
                {n.target_audience.toUpperCase()}
              </Badge>
              <Text size="xs" c="dimmed">
                {new Date(n.created_at).toLocaleDateString()}
              </Text>
            </Group>
            <Title order={4} mb="xs">{n.title}</Title>
            <Text size="sm" c="dimmed" mb="md" style={{ whiteSpace: "pre-line" }}>
              {n.content}
            </Text>
            <Group justify="space-between" pt="xs" style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}>
              <Text size="xs" fw={500} c="gray.7">
                {n.hostel_name ? `Hostel: ${n.hostel_name}` : "All Hostels (Institute-wide)"}
              </Text>
              {n.expires_at && (
                <Text size="xs" c="orange">Expires: {n.expires_at}</Text>
              )}
            </Group>
          </Card>
        ))}
      </SimpleGrid>

      {/* Modal: Publish Notice */}
      <Modal opened={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Publish Notice Circular" centered>
        <Stack gap="sm">
          <Select
            label="Target Hostel (Leave blank for institute-wide)"
            placeholder="Institute-wide / All Hostels"
            clearable
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={noticeHostelId}
            onChange={setNoticeHostelId}
          />
          <TextInput label="Notice Title / Header" placeholder="e.g. Scheduled Water Maintenance Shutdown" required value={title} onChange={(e) => setTitle(e.target.value)} />
          <Select
            label="Audience"
            required
            data={[
              { value: "all", label: "Everyone (Students & Staff)" },
              { value: "students", label: "Hostel Students Only" },
              { value: "caretakers", label: "Caretakers & Maintenance" },
              { value: "wardens", label: "Wardens & Admin" },
            ]}
            value={targetAudience}
            onChange={(val) => val && setTargetAudience(val)}
          />
          <Textarea label="Notice Body / Instructions" minRows={4} required value={content} onChange={(e) => setContent(e.target.value)} />
          <TextInput label="Expiry Date" type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            <Button loading={createNotice.isPending} onClick={handleCreate}>Publish</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
