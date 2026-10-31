import { Alert, Container } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";

export default function YearEndProcessingPage() {
  return (
    <Container size="md">
      <PageHeader title="Year-End Leave Processing" />
      <Alert color="blue">
        Year-end leave accounting runs from the configured system event. This page
        does not trigger the operation manually.
      </Alert>
    </Container>
  );
}
