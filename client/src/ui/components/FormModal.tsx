import { Box, Button, Group, Modal, ScrollArea, Text } from "@mantine/core";

import { ErrorState } from "./ErrorState";

/** Distilled from the sysadmin client's AddBatchModal: padding={0}, no default
 *  close button, a gradient header band and a bordered footer. Keeping that
 *  shape here is what makes a modal in this module look like one in the
 *  operator console. */
export function FormModal({
  opened, onClose, title, subtitle, children, onSubmit, submitLabel = "Save",
  submitting, error, danger, disabled, disabledReason, size = "lg",
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
  /** Shown beside a disabled action: a greyed-out button with no stated reason
   *  leaves the user guessing which field is at fault. */
  disabledReason?: string;
  size?: string;
}) {
  return (
    <Modal
      opened={opened} onClose={onClose} padding={0} radius="md" size={size}
      withCloseButton={false} centered
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

      {/* Only the body scrolls. With the whole modal scrolling, a long form
          pushed Cancel and Save off-screen and the user had to hunt for them. */}
      <ScrollArea.Autosize mah="min(60vh, 34rem)" type="auto">
        <Box px="lg" py="lg">
          {error != null && <Box mb="md"><ErrorState error={error} /></Box>}
          {children}
        </Box>
      </ScrollArea.Autosize>

      <Group
        justify="space-between" wrap="nowrap" px="lg" py="md"
        style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}
      >
        <Text size="xs" c="dimmed" lineClamp={2}>
          {disabled && disabledReason ? disabledReason : ""}
        </Text>
        <Group gap="sm" wrap="nowrap">
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
      </Group>
    </Modal>
  );
}
