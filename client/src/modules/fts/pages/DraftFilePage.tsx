import { useState } from "react";
import { Alert, Button, Group, Loader, Stack, Textarea, TextInput, Title } from "@mantine/core";
import { useNavigate, useParams } from "react-router-dom";
import { errorMessage, useCreateFile, useDiscardDraft, useFile, useUpdateFile } from "../api/hooks";

const DraftFilePage = () => {
  const params = useParams();
  const id = params.id ? Number(params.id) : NaN;
  const isEdit = Number.isFinite(id);
  const navigate = useNavigate();

  const { data: file, isLoading } = useFile(id);
  const create = useCreateFile();
  const update = useUpdateFile(id);
  const discard = useDiscardDraft(id);

  const [subjectInput, setSubjectInput] = useState<string | null>(null);
  const [commentInput, setCommentInput] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const handleSave = () => {
    const subject = subjectInput ?? file?.subject ?? "";
    const comment = commentInput ?? file?.comment ?? "";

    if (comment.trim() === "") {
      setProblem("A comment is required");
      return;
    }

    setProblem(null);

    if (isEdit && file?.permissions.can_edit_draft) {
      update.mutate({ subject, comment }, { onSuccess: () => navigate(`/fts/files/${id}`) });
    } else {
      create.mutate({ subject, comment }, { onSuccess: (data) => navigate(`/fts/files/${data.id}`) });
    }
  };

  return (
    <Stack>
      {isEdit && isLoading && <Loader />}
      {problem && <Alert color="red">{problem}</Alert>}
      {(create.error ?? update.error ?? discard.error) && (
        <Alert color="red">{errorMessage(create.error ?? update.error ?? discard.error)}</Alert>
      )}
      <Title>{isEdit ? "Edit draft" : "Create file"}</Title>
      <TextInput
        label="Subject"
        value={subjectInput ?? file?.subject ?? ""}
        onChange={(e) => setSubjectInput(e.target.value)}
      />
      <Textarea
        label="Comment"
        value={commentInput ?? file?.comment ?? ""}
        onChange={(e) => setCommentInput(e.target.value)}
      />
      <Group justify="flex-end">
        {isEdit && file?.permissions.can_edit_draft && (
          <Button color="red" onClick={() => discard.mutate(undefined, { onSuccess: () => navigate("/fts/drafts") })}>
            Discard draft
          </Button>
        )}
        <Button onClick={handleSave}>Save</Button>
      </Group>
    </Stack>
  );
};

export default DraftFilePage;
