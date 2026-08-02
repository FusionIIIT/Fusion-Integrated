import { Alert, Text } from "@mantine/core";
import { FaExclamationTriangle } from "react-icons/fa";

import { errorMessage, requestId } from "../../lib/http";

export function ErrorState({ error }: { error: unknown }) {
  const rid = requestId(error);
  return (
    <Alert
      color="red" variant="light" icon={<FaExclamationTriangle />}
      title="Could not load this"
    >
      <Text size="sm">{errorMessage(error)}</Text>
      {rid && (
        // The one id support can grep. Always show it.
        <Text size="xs" c="dimmed" mt={6} ff="monospace">
          Reference: {rid}
        </Text>
      )}
    </Alert>
  );
}
