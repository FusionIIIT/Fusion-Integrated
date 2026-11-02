/* eslint-disable react/prop-types */
import { useState } from "react";
import { Box, CloseButton, Group, Modal, ScrollArea, SegmentedControl, Select, Stack, Text, ThemeIcon } from "@mantine/core";
import { FaUserPlus } from "react-icons/fa";
import ExcelUploadFlow from "./ExcelUploadFlow";
import ManualEntryForm from "./ManualEntryForm";

const AddStudentsModal = ({ opened, onClose, config, onSaved }) => {
  const [mode, setMode] = useState("excel");
  const [academicYear, setAcademicYear] = useState(String(config.yearOptions[0]));

  const handleSaved = () => onSaved?.();

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="80%"
      radius="md"
      padding={0}
      withCloseButton={false}
      overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
    >
      <Box
        p="lg"
        style={{
          background: "linear-gradient(135deg, var(--mantine-color-indigo-7), var(--mantine-color-blue-9))",
          color: "white",
        }}
      >
        <Group justify="space-between" wrap="nowrap">
          <Group gap="md" wrap="nowrap">
            <ThemeIcon size={44} radius="md" variant="white" color="indigo">
              <FaUserPlus size={17} />
            </ThemeIcon>
            <div>
              <Text fw={700} size="lg" c="white">
                Add {config.label} Students
              </Text>
              <Text size="sm" c="rgba(255,255,255,0.85)">
                Bulk-upload an Excel sheet or add a single student manually
              </Text>
            </div>
          </Group>
          <CloseButton onClick={onClose} size="lg" c="white" variant="transparent" aria-label="Close" />
        </Group>
      </Box>

      <Box
        px="lg"
        py="md"
        style={{ borderBottom: "1px solid var(--mantine-color-gray-2)", background: "var(--mantine-color-gray-0)" }}
      >
        <Group justify="space-between" align="flex-end" wrap="wrap" gap="sm">
          <SegmentedControl
            size="md"
            radius="md"
            value={mode}
            onChange={setMode}
            data={[
              { label: "Excel Upload", value: "excel" },
              { label: "Manual Entry", value: "manual" },
            ]}
          />
          <Select
            label="Admission year"
            data={config.yearOptions.map(String)}
            value={academicYear}
            onChange={(value) => setAcademicYear(value || String(config.yearOptions[0]))}
            size="md"
            radius="md"
            w={160}
          />
        </Group>
        <Text size="xs" c="dimmed" mt="xs">
          Students will be admitted into {config.label} batches for {academicYear}. A matching running batch must exist for that year.
        </Text>
      </Box>

      <ScrollArea.Autosize mah="64vh">
        <Stack p="lg">
          {mode === "excel" ? (
            <ExcelUploadFlow config={config} academicYear={academicYear} onSaved={handleSaved} onCancel={onClose} />
          ) : (
            <ManualEntryForm config={config} academicYear={academicYear} onSubmitted={handleSaved} onCancel={onClose} />
          )}
        </Stack>
      </ScrollArea.Autosize>
    </Modal>
  );
};

export default AddStudentsModal;
