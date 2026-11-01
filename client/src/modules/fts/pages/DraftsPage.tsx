import { Alert, Button, Loader, Stack, Title } from "@mantine/core";
import { errorMessage, useDrafts } from "../api/hooks";
import FileTable from "../components/FileTable";

function DraftsPage() {
  const { data, isLoading, error } = useDrafts();

  return (
    <Stack gap="md">
      <Title order={2}>My drafts</Title>
      <Button component="a" href="/fts/files/new" variant="outline">Create file</Button>
      {isLoading && <Loader />}
      {error && <Alert color="red">{errorMessage(error)}</Alert>}
      {!isLoading && !error && <FileTable files={data ?? []} emptyText="No drafts." />}
    </Stack>
  );
}

export { DraftsPage };
export default DraftsPage;
