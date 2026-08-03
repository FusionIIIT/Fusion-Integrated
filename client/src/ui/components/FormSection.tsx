import { Box, Divider, Grid, Stack, Text } from "@mantine/core";

/** A titled group of fields.
 *
 *  A form long enough to scroll needs structure, or every control reads as
 *  equally important and the eye has nothing to anchor on. */
export function FormSection({ title, hint, children, first }: {
  title: string;
  hint?: string;
  children: React.ReactNode;
  /** Skips the leading divider on the first section. */
  first?: boolean;
}) {
  return (
    <Box>
      {!first && <Divider mb="lg" />}
      <Stack gap={2} mb="sm">
        <Text fw={600} size="sm">{title}</Text>
        {hint && <Text size="xs" c="dimmed">{hint}</Text>}
      </Stack>
      {children}
    </Box>
  );
}

/** A 12-column row. Children pick their own spans; on a narrow screen every
 *  field goes full width. */
export function FormRow({ children }: { children: React.ReactNode }) {
  return <Grid gutter="md">{children}</Grid>;
}

/** One field in a FormRow. `span` is the desktop width in twelfths. */
export function Field({ span = 6, children }: {
  span?: number;
  children: React.ReactNode;
}) {
  return <Grid.Col span={{ base: 12, sm: span }}>{children}</Grid.Col>;
}
