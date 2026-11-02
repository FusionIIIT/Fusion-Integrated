/* eslint-disable react/prop-types */
import { useMemo, useState } from "react";
import { Box, Button, CloseButton, Group, Modal, NumberInput, Select, Stack, Text, ThemeIcon } from "@mantine/core";
import { FaLayerGroup } from "react-icons/fa";
import { notifications } from "@mantine/notifications";
import { createBatch } from "../../../api/UpcomingBatches";

const AddBatchModal = ({ opened, onClose, config, disciplines, curriculums, onCreated }) => {
  const [programme, setProgramme] = useState(null);
  const [disciplineId, setDisciplineId] = useState(null);
  const [year, setYear] = useState(String(config.yearOptions[0]));
  const [totalSeats, setTotalSeats] = useState(60);
  const [curriculumId, setCurriculumId] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const disciplineOptions = useMemo(() => {
    const allowed = programme ? config.disciplineMap[programme] || [] : [];
    return disciplines
      .filter((d) => allowed.includes(d.name))
      .map((d) => ({ value: String(d.id), label: `${d.name} (${d.acronym})` }));
  }, [programme, disciplines, config]);

  const curriculumOptions = useMemo(
    () => curriculums.map((c) => ({ value: String(c.id), label: `${c.name} v${c.version}` })),
    [curriculums],
  );

  const reset = () => {
    setProgramme(null);
    setDisciplineId(null);
    setYear(String(config.yearOptions[0]));
    setTotalSeats(60);
    setCurriculumId(null);
  };

  const handleSubmit = async () => {
    if (!programme || !disciplineId || !year || !totalSeats) {
      notifications.show({ title: "Missing fields", message: "Programme, discipline, year and seats are required.", color: "red" });
      return;
    }
    setSubmitting(true);
    try {
      const res = await createBatch({
        programme,
        discipline: Number(disciplineId),
        year: Number(year),
        total_seats: Number(totalSeats),
        curriculum: curriculumId ? Number(curriculumId) : null,
      });
      if (res.success) {
        notifications.show({ title: "Success", message: res.message, color: "green" });
        reset();
        onCreated?.();
        onClose();
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Failed to create batch.", color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      centered
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
              <FaLayerGroup size={18} />
            </ThemeIcon>
            <div>
              <Text fw={700} size="lg" c="white">
                Add {config.label} Batch
              </Text>
              <Text size="sm" c="rgba(255,255,255,0.85)">
                Create a new admission batch and allocate seats
              </Text>
            </div>
          </Group>
          <CloseButton onClick={onClose} size="lg" c="white" variant="transparent" aria-label="Close" />
        </Group>
      </Box>

      <Stack gap="md" p="lg">
        <Select
          label="Programme"
          placeholder="Select programme"
          data={config.programmeOptions}
          value={programme}
          onChange={(value) => {
            setProgramme(value);
            setDisciplineId(null);
          }}
          size="md"
          radius="md"
          required
        />
        <Select
          label="Discipline"
          placeholder={programme ? "Select discipline" : "Select a programme first"}
          data={disciplineOptions}
          value={disciplineId}
          onChange={setDisciplineId}
          disabled={!programme}
          size="md"
          radius="md"
          searchable
          required
        />
        <Group grow align="flex-start">
          <Select
            label="Batch Year"
            data={config.yearOptions.map(String)}
            value={year}
            onChange={setYear}
            size="md"
            radius="md"
            required
          />
          <NumberInput label="Total Seats" min={1} value={totalSeats} onChange={setTotalSeats} size="md" radius="md" required />
        </Group>
        <Select
          label="Curriculum (optional)"
          placeholder="Assign a working curriculum"
          data={curriculumOptions}
          value={curriculumId}
          onChange={setCurriculumId}
          size="md"
          radius="md"
          searchable
          clearable
        />
      </Stack>

      <Group
        justify="flex-end"
        p="md"
        style={{ borderTop: "1px solid var(--mantine-color-gray-3)", background: "var(--mantine-color-body)" }}
      >
        <Button variant="default" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} loading={submitting}>
          Create Batch
        </Button>
      </Group>
    </Modal>
  );
};

export default AddBatchModal;
