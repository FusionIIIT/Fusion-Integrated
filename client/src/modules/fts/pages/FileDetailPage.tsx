import { useState } from "react";
import { Alert, Badge, Button, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { Link, useParams } from "react-router-dom";
import { errorMessage, useArchiveFile, useFile, useFileHistory } from "../api/hooks";
import HistoryList from "../components/HistoryList";
import MovementModal from "../components/MovementModal";

const FileDetailPage: React.FC = () => {
  const id = Number(useParams().id);
  const { data: file, isLoading, error } = useFile(id);
  const { data: history } = useFileHistory(id);
  const archive = useArchiveFile(id);
  const [modal, setModal] = useState<"forward" | "return" | null>(null);

  if (isLoading) {
    return <Loader />;
  }

  if (error) {
    return <Alert color="red">{errorMessage(error)}</Alert>;
  }

  return (
    <Stack>
      <Title order={2}>{file?.subject}</Title>
      <Badge color={file?.status === "archived" ? "gray" : file?.status === "circulated" ? "blue" : "green"}>{file?.status}</Badge>
      <Text>Owner: {file?.owner_name}</Text>
      <Text>Current Holder: {file?.holder_name ?? "-"}</Text>
      <Text>Comment: {file?.comment}</Text>
      <Text>Attachments: {file?.attachments.join(", ")}</Text>
      {file?.status === "archived" && <Badge color="gray">Read-only</Badge>}
      {file?.status !== "archived" && (
        <Group>
          {file?.permissions.can_edit_draft && <Button component={Link} to={`/fts/files/${id}/edit`}>Edit draft</Button>}
          {file?.permissions.can_forward && <Button onClick={() => setModal("forward")}>Forward</Button>}
          {file?.permissions.can_return && <Button onClick={() => setModal("return")}>Return</Button>}
          {file?.permissions.can_archive && <Button onClick={() => { if (window.confirm("Archive this file?")) archive.mutate(); }}>Archive</Button>}
        </Group>
      )}
      <MovementModal opened={modal !== null} onClose={() => setModal(null)} fileId={id} mode={modal ?? "forward"} />
      <Title order={3}>Tracking history</Title>
      <HistoryList events={history ?? []} />
    </Stack>
  );
};

export default FileDetailPage;
export { FileDetailPage };
