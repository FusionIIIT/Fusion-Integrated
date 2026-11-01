/* eslint-disable react/prop-types */
import { useEffect, useMemo, useState } from "react";
import { ActionIcon, Badge, Box, Button, Center, Group, Loader, Menu, Modal, Table, Text, TextInput, Tooltip, UnstyledButton } from "@mantine/core";
import { FaCheck, FaChevronDown, FaEdit, FaEye, FaSearch, FaTrash } from "react-icons/fa";
import { notifications } from "@mantine/notifications";
import { deleteStudent, fetchBatchStudents, updateStudentStatus } from "../../../api/UpcomingBatches";
import { STATUS_COLOR, STATUS_OPTIONS } from "../config/studentFields";

const statusLabel = (value) => STATUS_OPTIONS.find((o) => o.value === value)?.label || value;
import StudentDetailModal from "./StudentDetailModal";
import EditStudentModal from "./EditStudentModal";

const StudentListModal = ({ opened, onClose, batch, config, onChanged }) => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState(null);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [statusBusy, setStatusBusy] = useState(null);

  useEffect(() => {
    if (!opened || !batch) return;
    setQuery("");
    setLoading(true);
    fetchBatchStudents(batch.batch_id)
      .then((data) => setStudents(data.students || []))
      .catch(() => notifications.show({ title: "Error", message: "Failed to load students.", color: "red" }))
      .finally(() => setLoading(false));
  }, [opened, batch]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return students;
    return students.filter(
      (s) => (s.name || "").toLowerCase().includes(term) || (s.roll_number || "").toLowerCase().includes(term),
    );
  }, [students, query]);

  const patchRow = (updated) => setStudents((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));

  const handleStatus = async (student, status) => {
    setStatusBusy(student.id);
    try {
      const res = await updateStudentStatus(student.id, status);
      if (res.success) {
        patchRow(res.student);
        notifications.show({ title: "Status updated", message: res.message, color: "green" });
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Failed to update status.", color: "red" });
    } finally {
      setStatusBusy(null);
    }
  };

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      const res = await deleteStudent(pendingDelete.id);
      if (res.success) {
        setStudents((prev) => prev.filter((s) => s.id !== pendingDelete.id));
        notifications.show({ title: "Deleted", message: res.message, color: "red" });
        onChanged?.();
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Failed to delete student.", color: "red" });
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  return (
    <>
      <Modal
        opened={opened}
        onClose={onClose}
        size="90%"
        title={batch ? `${batch.name} · ${batch.discipline} · ${batch.year}` : "Students"}
      >
        <TextInput
          mb="md"
          placeholder="Search by name or roll number"
          leftSection={<FaSearch size={12} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          size="md"
        />
        {loading ? (
          <Center h={200}>
            <Loader />
          </Center>
        ) : filtered.length === 0 ? (
          <Text ta="center" c="dimmed" py="xl">
            No students found.
          </Text>
        ) : (
          <>
            <Text size="sm" c="dimmed" mb="xs">
              {filtered.length} student(s)
            </Text>
            <Table.ScrollContainer minWidth={980}>
              <Table striped highlightOnHover verticalSpacing="sm" stickyHeader>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Roll No.</Table.Th>
                    <Table.Th>Name</Table.Th>
                    <Table.Th>Branch</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Gender</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {filtered.map((s) => (
                    <Table.Tr key={s.id}>
                      <Table.Td>{s.roll_number || "—"}</Table.Td>
                      <Table.Td fw={500}>{s.name}</Table.Td>
                      <Table.Td>
                        {s.branch}
                        {s.specialization ? ` · ${s.specialization}` : ""}
                      </Table.Td>
                      <Table.Td>{s.category}</Table.Td>
                      <Table.Td>{s.gender}</Table.Td>
                      <Table.Td>
                        <Menu position="bottom-start" width={180} shadow="md" withinPortal disabled={statusBusy === s.id}>
                          <Menu.Target>
                            <UnstyledButton aria-label="Change status" disabled={statusBusy === s.id}>
                              <Badge
                                color={STATUS_COLOR[s.reported_status] || "gray"}
                                variant="light"
                                size="lg"
                                radius="sm"
                                style={{ cursor: "pointer", textTransform: "none" }}
                                rightSection={<FaChevronDown size={9} />}
                              >
                                {statusLabel(s.reported_status)}
                              </Badge>
                            </UnstyledButton>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Label>Set reported status</Menu.Label>
                            {STATUS_OPTIONS.map((o) => (
                              <Menu.Item
                                key={o.value}
                                onClick={() => o.value !== s.reported_status && handleStatus(s, o.value)}
                                leftSection={
                                  <Box
                                    w={9}
                                    h={9}
                                    style={{
                                      borderRadius: "50%",
                                      background: `var(--mantine-color-${STATUS_COLOR[o.value] || "gray"}-6)`,
                                    }}
                                  />
                                }
                                rightSection={o.value === s.reported_status ? <FaCheck size={10} /> : null}
                              >
                                {o.label}
                              </Menu.Item>
                            ))}
                          </Menu.Dropdown>
                        </Menu>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={6} wrap="nowrap">
                          <Tooltip label="View details" withArrow>
                            <ActionIcon variant="light" onClick={() => setDetail(s)}>
                              <FaEye size={13} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Edit" withArrow>
                            <ActionIcon variant="light" color="indigo" onClick={() => setEditing(s)}>
                              <FaEdit size={13} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Delete" withArrow>
                            <ActionIcon variant="light" color="red" onClick={() => setPendingDelete(s)}>
                              <FaTrash size={13} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </>
        )}
      </Modal>

      <StudentDetailModal opened={!!detail} onClose={() => setDetail(null)} student={detail} />
      <EditStudentModal
        opened={!!editing}
        onClose={() => setEditing(null)}
        student={editing}
        config={config}
        onSaved={(updated) => {
          patchRow(updated);
          onChanged?.();
        }}
      />

      <Modal opened={!!pendingDelete} onClose={() => setPendingDelete(null)} title="Delete student" centered>
        <Text size="sm">
          Delete <strong>{pendingDelete?.name}</strong> ({pendingDelete?.roll_number || "no roll no."})? This cannot
          be undone.
        </Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={() => setPendingDelete(null)}>
            Cancel
          </Button>
          <Button color="red" onClick={confirmDelete} loading={deleting}>
            Delete
          </Button>
        </Group>
      </Modal>
    </>
  );
};

export default StudentListModal;
