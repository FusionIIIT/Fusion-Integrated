/* eslint-disable react/prop-types */
import { useMemo, useState } from "react";
import { Button, Center, Group, Loader, Modal, Paper, Select, Stack, Text, TextInput } from "@mantine/core";
import { FaFilter, FaPlus, FaSearch, FaUserPlus } from "react-icons/fa";
import { notifications } from "@mantine/notifications";
import { deleteBatch as deleteBatchApi } from "../../../api/UpcomingBatches";
import BatchTable from "./BatchTable";
import AddBatchModal from "./AddBatchModal";
import AddStudentsModal from "./AddStudentsModal";
import StudentListModal from "./StudentListModal";

const BatchSection = ({ config, batches, disciplines, curriculums, loading, refresh }) => {
  const [search, setSearch] = useState("");
  const [filterYear, setFilterYear] = useState(String(config.yearOptions[0]));
  const [addBatchOpen, setAddBatchOpen] = useState(false);
  const [addStudentsOpen, setAddStudentsOpen] = useState(false);
  const [viewBatch, setViewBatch] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const filtered = useMemo(() => {
    let list = batches;
    if (filterYear !== "all") list = list.filter((b) => String(b.year) === filterYear);
    const term = search.trim().toLowerCase();
    if (term) {
      list = list.filter(
        (b) =>
          b.name.toLowerCase().includes(term) ||
          b.discipline.toLowerCase().includes(term) ||
          String(b.year).includes(term),
      );
    }
    return list;
  }, [batches, search, filterYear]);

  const yearOptions = [
    { value: "all", label: "All years" },
    ...config.yearOptions.map((y) => ({ value: String(y), label: String(y) })),
  ];

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      const res = await deleteBatchApi(pendingDelete.batch_id);
      if (res.success) {
        notifications.show({ title: "Deleted", message: res.message, color: "green" });
        setPendingDelete(null);
        refresh();
      } else {
        notifications.show({ title: "Cannot delete", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Failed to delete batch.", color: "red" });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Stack gap="md">
      <Paper p="md" radius="md" withBorder>
        <Group justify="space-between" wrap="wrap" gap="sm">
          <TextInput
            placeholder="Search batches"
            leftSection={<FaSearch size={12} />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            size="md"
            w={280}
          />
          <Group gap="sm">
            <Select
              leftSection={<FaFilter size={12} />}
              data={yearOptions}
              value={filterYear}
              onChange={(value) => setFilterYear(value || "all")}
              size="md"
              w={160}
              aria-label="Filter by year"
            />
            <Button size="md" variant="light" leftSection={<FaPlus size={12} />} onClick={() => setAddBatchOpen(true)}>
              Add Batch
            </Button>
            <Button size="md" leftSection={<FaUserPlus size={12} />} onClick={() => setAddStudentsOpen(true)}>
              Add Students
            </Button>
          </Group>
        </Group>
      </Paper>

      <Paper p={0} radius="md" withBorder>
        {loading ? (
          <Center h={200}><Loader /></Center>
        ) : (
          <BatchTable batches={filtered} onView={setViewBatch} onDelete={setPendingDelete} />
        )}
      </Paper>

      <AddBatchModal
        opened={addBatchOpen}
        onClose={() => setAddBatchOpen(false)}
        config={config}
        disciplines={disciplines}
        curriculums={curriculums}
        onCreated={refresh}
      />
      <AddStudentsModal
        opened={addStudentsOpen}
        onClose={() => setAddStudentsOpen(false)}
        config={config}
        onSaved={refresh}
      />
      <StudentListModal
        opened={!!viewBatch}
        onClose={() => setViewBatch(null)}
        batch={viewBatch}
        config={config}
        onChanged={refresh}
      />

      <Modal opened={!!pendingDelete} onClose={() => setPendingDelete(null)} title="Delete batch" centered>
        <Text size="sm">
          Delete batch {pendingDelete?.name} · {pendingDelete?.discipline} · {pendingDelete?.year}? This cannot be undone.
        </Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={() => setPendingDelete(null)}>Cancel</Button>
          <Button color="red" onClick={confirmDelete} loading={deleting}>Delete</Button>
        </Group>
      </Modal>
    </Stack>
  );
};

export default BatchSection;
