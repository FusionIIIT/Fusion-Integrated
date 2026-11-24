import { Box, Card, Container, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { FaInbox } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";

// Every page's loading, error and empty states, so none of them can spin forever.
export function PageBody({ isPending, error, isEmpty, emptyTitle, header, overlays, children }: {
  isPending: boolean;
  error: unknown;
  isEmpty: boolean;
  emptyTitle: string;
  header: React.ReactNode;
  overlays?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Container size="lg">
      {header}
      {error ? <ErrorState error={error} />
        : isPending ? <Text c="dimmed">Loading…</Text>
          : isEmpty ? (
            <Card padding="xl" withBorder>
              <Stack align="center" gap={6}>
                <FaInbox size={22} aria-hidden />
                <Text fw={600}>{emptyTitle}</Text>
              </Stack>
            </Card>
          ) : children}
      {overlays}
    </Container>
  );
}

// The server's refusal of a row action, shown as sent (Step 6.8).
export function ActionError({ errors }: { errors: unknown[] }) {
  const error = errors.find((e) => e != null);
  return error ? <Box mb="md"><ErrorState error={error} /></Box> : null;
}

// Keeps a closing dialog's content on screen until its fade-out ends.
export function useDialog<T>() {
  const [dialog, setState] = useState<T | null>(null);
  const [opened, setOpened] = useState(false);
  const setDialog = (next: T | null) => {
    if (next === null) setOpened(false);
    else { setState(next); setOpened(true); }
  };
  return { dialog, setDialog, opened };
}
