import { Alert, Loader, Stack, Title } from "@mantine/core";
import { errorMessage, useOutbox } from "../api/hooks";
import FileTable from "../components/FileTable";

function OutboxPage() {
  const { data, isLoading, error } = useOutbox();

  return (
    <Stack gap="md">
      <Title order={2}>Outbox</Title>
      {isLoading && <Loader />}
      {error && <Alert color="red">{errorMessage(error)}</Alert>}
      {!isLoading && !error && <FileTable files={data ?? []} emptyText="No files sent." />}
    </Stack>
  );
}

export { OutboxPage };
export default OutboxPage;
