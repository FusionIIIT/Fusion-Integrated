import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button, Group, Select, Stack, TextInput, Textarea,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateDraft } from "../api/hooks";
import type { Priority } from "../api/types";
import { FtsError } from "../components/FtsError";

const PRIORITIES = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

/** FTS-UC-001. The initial comment is mandatory (BR-FTS-004). */
export function CreateFilePage() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const create = useCreateDraft();

  const [subject, setSubject] = useState("");
  const [comment, setComment] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [category, setCategory] = useState("general");
  const [problem, setProblem] = useState("");

  function submit() {
    if (!subject.trim()) return setProblem("A subject is required.");
    if (!comment.trim()) return setProblem("An initial comment is required.");
    setProblem("");
    create.mutate(
      {
        subject: subject.trim(),
        initial_comment: comment.trim(),
        description: description.trim(),
        priority,
        category: category.trim() || "general",
        creator_role: session?.active_role || "Employee",
      },
      { onSuccess: (r) => navigate(`/fts/files/${r.file_id}`) },
    );
  }

  return (
    <>
      <PageHeader
        title="New file"
        subtitle="Saved as a draft. Send it from its page when it is ready."
      />
      <Stack gap="md" maw={640}>
        {problem && <FtsError error={{ response: { data: { error: problem } } }} />}
        {create.error != null && <FtsError error={create.error} />}
        <TextInput
          label="Subject" required value={subject}
          onChange={(e) => setSubject(e.currentTarget.value)}
        />
        <Textarea
          label="Initial comment" required minRows={3} autosize value={comment}
          onChange={(e) => setComment(e.currentTarget.value)}
        />
        <Textarea
          label="Description (optional)" minRows={2} autosize value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
        />
        <Group grow align="flex-start">
          <Select
            label="Priority" data={PRIORITIES} value={priority} allowDeselect={false}
            onChange={(v) => v && setPriority(v as Priority)}
          />
          <TextInput
            label="Category" value={category}
            onChange={(e) => setCategory(e.currentTarget.value)}
          />
        </Group>
        <Group>
          <Button onClick={submit} loading={create.isPending}>Save draft</Button>
          <Button variant="default" onClick={() => navigate("/fts/drafts")}>
            Cancel
          </Button>
        </Group>
      </Stack>
    </>
  );
}

export default CreateFilePage;
