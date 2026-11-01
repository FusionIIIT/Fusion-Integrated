import { useParams } from "react-router-dom";
import { Alert, Badge, Button, Loader, Stack, Title } from "@mantine/core";
import { useFile, useFileHistory, useArchiveFile } from "../api/hooks";
import FileTable from "../components/FileTable";
import HistoryList from "../components/HistoryList";
import MovementModal from "../components/MovementModal";

function FileDetailPage() {
  const { id } = useParams();
  const fileId = Number(id);
  const { data: file, isLoading, error } = useFile(fileId);
  const { data: history } = useFileHistory(fileId);
  const archiveFile = useArchiveFile();

  if (isLoading) {
    return <Loader />;
  }

  if (error) {
    return <Alert color="red">{errorMessage(error)}</Alert>;
  }

  if (!file) {
    return <Alert color="red">File not found.</Alert>;
  }

  return (
    <Stack gap="md">
      <Title order={2}>{file.subject}</Title>
      <Badge color={file.status === "draft" ? "green" : "red"}>{file.status}</Badge>
      {file.status === "archived" && <Badge color="gray">Read-only</Badge>}
      <Text>Owner: {file.owner_name}</Text>
      <Text>Holder: {file.holder_name ? file.holder_name : "-"}</Text>
      <Text>Comment: {file.comment}</Text>
      <FileTable files={file.attachments} emptyText="No attachments." />
      {file.status !== "archived" && (
        <>
          {file.permissions.can_edit_draft && (
            <Button component={Link} to={`/fts/files/${fileId}/edit`}>Edit draft</Button>
          )}
          {file.permissions.can_forward && (
            <MovementModal fileId={fileId} mode="forward" />
          )}
          {file.permissions.can_return && (
            <MovementModal fileId={fileId} mode="return" />
          )}
          {file.permissions.can_archive && (
            <Button onClick={() => {
              if (window.confirm("Are you sure you want to archive this file?")) {
                archiveFile.mutate(fileId);
              }
            }}>Archive</Button>
          )}
        </>
      )}
      <Title order={2}>Tracking history</Title>
      <HistoryList events={history ?? []} />
    </Stack>
  );
}

export { FileDetailPage };
export default FileDetailPage;
