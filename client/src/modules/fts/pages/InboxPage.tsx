import { Alert, Loader, Stack, Title } from "@mantine/core";
import { errorMessage, useInbox } from "../api/hooks";
import FileTable from "../components/FileTable";

function InboxPage() {
  const { data, isLoading, error } = useInbox();

  return (
    <Stack gap="md">
      <Title order={2}>Inbox</Title>
      {isLoading && <Loader />}
      {error && <Alert color="red">{errorMessage(error)}</Alert>}
      {!isLoading && !error && <FileTable files={data ?? []} emptyText="No files received." />}
    </Stack>
  );
}

export { InboxPage };
export default InboxPage;
