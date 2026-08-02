import { Box, Button, Group, Modal, ScrollArea, Text } from "@mantine/core";

import { ErrorState } from "./ErrorState";

/** Distilled from the sysadmin client's AddBatchModal: padding={0}, no default
 *  close button, a gradient header band and a bordered footer. Keeping that
 *  shape here is what makes a modal in this module look like one in the
 *  operator console. */
export function FormModal({
  opened, onClose, title, subtitle, children, onSubmit, submitLabel = "Save",
  submitting, error, danger, disabled,
}: {
  opened: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onSubmit: () => void;
  submitLabel?: string;
  submitting?: boolean;
  error?: unknown;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <Modal
      opened={opened} onClose={onClose} padding={0} radius="md" size="lg"
      withCloseButton={false} centered
      scrollAreaComponent={ScrollArea.Autosize}
    >
      <Box
        px="lg" py="md"
        style={{
          background: "linear-gradient(135deg, #0c1526 0%, #15304f 100%)",
          color: "#fff",
        }}
      >
        <Text fw={700} size="lg">{title}</Text>
        {subtitle && (
          <Text size="sm" c="rgba(255,255,255,.62)" mt={2}>{subtitle}</Text>
        )}
      </Box>

      <Box px="lg" py="lg">
        {error != null && <Box mb="md"><ErrorState error={error} /></Box>}
        {children}
      </Box>

      <Group
        justify="flex-end" px="lg" py="md"
        style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}
      >
        <Button variant="default" onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={onSubmit} loading={submitting} disabled={disabled}
          color={danger ? "red" : undefined}
        >
          {submitLabel}
        </Button>
      </Group>
    </Modal>
  );
}
