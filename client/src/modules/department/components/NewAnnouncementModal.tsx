import { useState } from "react";
import { Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { usePublishAnnouncement } from "../api/hooks";

interface Props {
  opened: boolean;
  onClose: () => void;
  departmentId: number;
}

export function NewAnnouncementModal({ opened, onClose, departmentId }: Props) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [programme, setProgramme] = useState("BTech");
  const [roleTarget, setRoleTarget] = useState("all");

  const publish = usePublishAnnouncement();

  const handleSubmit = async () => {
    if (!title.trim() || !body.trim()) return;
    try {
      await publish.mutateAsync({
        department: departmentId,
        title,
        body,
        academic_year: academicYear,
        programme,
        role_target: roleTarget,
      });
      notifications.show({
        title: "Announcement published",
        message: `"${title}" has been published.`,
        color: "teal",
      });
      setTitle("");
      setBody("");
      onClose();
    } catch (e) {
      notifications.show({
        title: "Failed to publish",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="New Announcement"
      subtitle="Publish an announcement for department members"
      onSubmit={handleSubmit}
      submitting={publish.isPending}
      disabled={!title.trim() || !body.trim()}
    >
      <Stack gap="sm">
        <TextInput
          label="Title"
          placeholder="e.g. End Semester Lab Examination Schedule"
          required
          value={title}
          onChange={(e) => setTitle(e.currentTarget.value)}
        />
        <Textarea
          label="Content"
          placeholder="Details of the announcement..."
          required
          minRows={4}
          value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
        />
        <Select
          label="Academic Year"
          data={["2024-2025", "2025-2026", "2026-2027"]}
          value={academicYear}
          onChange={(v) => setAcademicYear(v || "2026-2027")}
        />
        <Select
          label="Programme"
          data={["All", "BTech", "MTech", "PhD"]}
          value={programme}
          onChange={(v) => setProgramme(v || "All")}
        />
        <Select
          label="Target Audience"
          data={[
            { value: "all", label: "Everyone" },
            { value: "student", label: "Students only" },
            { value: "faculty", label: "Faculty only" },
          ]}
          value={roleTarget}
          onChange={(v) => setRoleTarget(v || "all")}
        />
      </Stack>
    </FormModal>
  );
}
