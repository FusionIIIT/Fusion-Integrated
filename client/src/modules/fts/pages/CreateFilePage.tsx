import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ftsApi } from "../api";
import type { EmployeeUser } from "../types";

export default function CreateFilePage() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const currentUserId = session?.user.id;

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [initialComment, setInitialComment] = useState("");
  const [isDraft, setIsDraft] = useState(false);
  const [receiverId, setReceiverId] = useState<string | null>(null);
  const [employeeOptions, setEmployeeOptions] = useState<
    Array<{ value: string; label: string }>
  >([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    ftsApi
      .searchEmployees("")
      .then((emps) => {
        setEmployeeOptions(
          emps
            .filter((e) => e.user_id !== currentUserId)
            .map((e: EmployeeUser) => ({
              value: String(e.user_id),
              label: `${e.display_name} (${e.username}) - ${e.department || e.kind}`,
            })),
        );
      })
      .catch((err) => {
        notifications.show({ color: "red", message: errorMessage(err) });
      });
  }, [currentUserId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) {
      notifications.show({ color: "red", message: "Subject is required." });
      return;
    }
    if (!initialComment.trim()) {
      notifications.show({
        color: "red",
        message: "An initial comment is mandatory.",
      });
      return;
    }
    if (!isDraft && !receiverId) {
      notifications.show({
        color: "red",
        message: "Please select a recipient to circulate the file.",
      });
      return;
    }

    setSubmitting(true);
    try {
      await ftsApi.createFile({
        subject,
        description,
        initial_comment: initialComment,
        is_draft: isDraft,
        receiver_id: isDraft ? null : Number(receiverId),
      });
      notifications.show({
        color: "green",
        message: isDraft
          ? "Draft saved successfully."
          : "File created and sent into circulation.",
      });
      navigate(isDraft ? "/fts/drafts" : "/fts/outbox");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Create New File"
        subtitle="Initiate an institutional file or save a working draft."
      />
      <Card withBorder p="lg" mt="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="File Subject"
              placeholder="e.g. Budget Sanction for Lab Equipment"
              value={subject}
              onChange={(e) => setSubject(e.currentTarget.value)}
              required
            />

            <Textarea
              label="Description (Optional)"
              placeholder="Detailed description of the file contents..."
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
              minRows={2}
            />

            <Textarea
              label="Initial Comment"
              placeholder="Mandatory initial note / remarks"
              value={initialComment}
              onChange={(e) => setInitialComment(e.currentTarget.value)}
              required
              minRows={3}
            />

            <Checkbox
              label="Save as working draft (do not circulate yet)"
              checked={isDraft}
              onChange={(e) => setIsDraft(e.currentTarget.checked)}
            />

            {!isDraft && (
              <Select
                label="Forward To (Recipient Employee)"
                placeholder="Search and select recipient"
                data={employeeOptions}
                value={receiverId}
                onChange={setReceiverId}
                searchable
                required
              />
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/fts/inbox")}>
                Cancel
              </Button>
              <Button type="submit" loading={submitting}>
                {isDraft ? "Save Draft" : "Circulate File"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
