import { Container } from "@mantine/core";

import { errorStatus } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { NotPermitted } from "../../../ui/components/NotPermitted";

/** A refusal means another role owns this page; anything else is a failure to report. */
export function PageError({ error }: { error: unknown }) {
  return (
    <Container size="xl" pt="md">
      {errorStatus(error) === 403 ? <NotPermitted /> : <ErrorState error={error} />}
    </Container>
  );
}
