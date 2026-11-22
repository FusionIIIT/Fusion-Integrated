import { Alert, Title } from "@mantine/core";

export default function BillingPage() {
  return (
    <>
      <Title order={2}>Billing</Title>
      <Alert mt="md" title="Billing view">
        Bills are generated and settled through booking detail actions.
      </Alert>
    </>
  );
}
