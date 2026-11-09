import { Alert } from "@mantine/core";

import { ftsErrorMessage } from "../lib/errors";

/** The platform's ErrorState cannot read FTS's {"error": "text"} replies. */
export function FtsError({ error, title }: { error: unknown; title?: string }) {
  return (
    <Alert color="red" variant="light" title={title}>
      {ftsErrorMessage(error)}
    </Alert>
  );
}

export default FtsError;
