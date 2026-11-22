import { Alert, Title } from "@mantine/core";

export default function ReportsPage() {
  return (
    <>
      <Title order={2}>VH reports</Title>
      <Alert mt="md" title="Report API available">
        Use the report endpoints for generated summaries.
      </Alert>
    </>
  );
}
