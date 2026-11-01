import { Alert, Button, Group, Loader, Stack, TextInput, Textarea } from "@mantine/core";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage, useCreateFile, useDiscardDraft, useFile, useUpdateFile } from "../api/hooks";
import { FileSummary, FileDetail, CreateFileInput, UpdateFileInput } from "../api/types";

function DraftFilePage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const queryClient = useQueryClient();
  const mode = id ? "edit" : "create";

  const { data: file, isLoading, error } = useQuery({ queryKey: ["fts", "file", id], queryFn: () => useFile(Number(id)).data, enabled: !!id });
  const createMutation = useCreateFile();
  const updateMutation = useUpdateFile(Number(id));
  const discardMutation = useDiscardDraft(Number(id));

  const [subject, setSubject] = useState(file?.subject || "");
  const [comment, setComment] = useState(file?.initial_comment || "");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!comment.trim()) {
      alert("A comment is required");
      return;
    }

    if (mode === "create") {
      const input: CreateFileInput = { subject, initial_comment: comment };
      try {
        const data = await createMutation.mutateAsync(input);
        navigate(`/fts/files/${data.id}`);
      } catch (e) {
        alert(errorMessage(e));
      }
    } else if (mode === "edit" && file?.permissions.can_edit_draft) {
      const input: UpdateFileInput = { subject, initial_comment: comment };
      try {
        await updateMutation.mutateAsync(input);
        navigate("/fts/drafts");
      } catch (e) {
        alert(errorMessage(e));
      }
    }
  };

  return (
    <Stack gap="md">
      <Title order={2}>{mode === "create" ? "Create Draft" : "Edit Draft"}</Title>
      {isLoading && <Loader />}
      {error && <Alert color="red">{errorMessage(error)}</Alert>}
      {!isLoading && !error && (
        <form onSubmit={handleSubmit}>
          <TextInput label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
          <Textarea label="Initial comment" value={comment} onChange={(e) => setComment(e.target.value)} required />
          <Group position="right">
            <Button type="submit">Save</Button>
            {mode === "edit" && file?.permissions.can_edit_draft && (
              <Button color="red" onClick={() => discardMutation.mutate()}>
                Discard draft
              </Button>
            )}
          </Group>
        </form>
      )}
    </Stack>
  );
}

export { DraftFilePage };
export default DraftFilePage;
