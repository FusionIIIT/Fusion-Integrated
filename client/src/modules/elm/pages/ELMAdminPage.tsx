import { useState, useEffect } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import type { LeaveRequest } from "../api/types";

export default function ELMAdminPage() {
  const [pendingRequests, setPendingRequests] = useState<LeaveRequest[]>([]);
  const [offlineOpened, setOfflineOpened] = useState(false);

  // Offline form state
  const [empId, setEmpId] = useState("");
  const [cat, setCat] = useState("CL");
  const [sDate, setSDate] = useState("");
  const [eDate, setEDate] = useState("");
  const [refNo, setRefNo] = useState("");
  const [offlineReason, setOfflineReason] = useState("");

  const fetchPending = async () => {
    try {
      const res = await fetch("/api/v1/elm/approvals/pending/");
      if (res.ok) {
        const data = await res.json();
        setPendingRequests(data);
      }
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleUnitHeadAction = async (id: number, action: string) => {
    try {
      const res = await fetch(`/api/v1/elm/approvals/${id}/unit-head-review/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, remarks: `Processed by Unit Head as ${action}` }),
      });
      if (res.ok) {
        notifications.show({ title: "Updated", message: `Request updated as ${action}.`, color: "green" });
        fetchPending();
      }
    } catch {
      notifications.show({ title: "Error", message: "Action failed.", color: "red" });
    }
  };

  const handleSanctionAction = async (id: number, action: string) => {
    try {
      const res = await fetch(`/api/v1/elm/approvals/${id}/sanction/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, remarks: `Processed by Sanction Authority as ${action}` }),
      });
      if (res.ok) {
        notifications.show({ title: "Updated", message: `Request sanctioned as ${action}.`, color: "green" });
        fetchPending();
      }
    } catch {
      notifications.show({ title: "Error", message: "Sanction failed.", color: "red" });
    }
  };

  const handleRecordOffline = async () => {
    try {
      const payload = {
        employee_id: parseInt(empId, 10),
        category: cat,
        start_date: sDate,
        end_date: eDate,
        sanction_reference: refNo,
        reason: offlineReason,
      };
      const res = await fetch("/api/v1/elm/admin/offline-record/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        notifications.show({ title: "Recorded", message: "Offline leave recorded.", color: "green" });
        setOfflineOpened(false);
        fetchPending();
      }
    } catch {
      notifications.show({ title: "Error", message: "Offline record failed.", color: "red" });
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="xl">
        <Group justify="space-between">
          <div>
            <Title order={2}>Leave Administration & Approval Queue</Title>
            <Text c="dimmed">Review subordinate leave requests, sanction higher leave, and manage records.</Text>
          </div>
          <Button onClick={() => setOfflineOpened(true)}>Record Offline Sanction</Button>
        </Group>

        <Card shadow="sm" radius="md" withBorder>
          <Title order={4} mb="md">Pending Review Queue</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Emp ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Decision Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pendingRequests.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    No pending requests in queue.
                  </Table.Td>
                </Table.Tr>
              ) : (
                pendingRequests.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.applicant_id}</Table.Td>
                    <Table.Td><Badge>{r.category}</Badge></Table.Td>
                    <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                    <Table.Td>{r.duration_days}</Table.Td>
                    <Table.Td><Badge color="yellow">{r.status}</Badge></Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {r.status === "AWAITING_UNIT_HEAD_REVIEW" && ["CL", "RH"].includes(r.category) && (
                          <>
                            <Button size="xs" color="green" onClick={() => handleUnitHeadAction(r.id, "APPROVE")}>Approve</Button>
                            <Button size="xs" color="red" variant="outline" onClick={() => handleUnitHeadAction(r.id, "REJECT")}>Reject</Button>
                          </>
                        )}
                        {r.status === "AWAITING_UNIT_HEAD_REVIEW" && !["CL", "RH"].includes(r.category) && (
                          <>
                            <Button size="xs" color="blue" onClick={() => handleUnitHeadAction(r.id, "RECOMMEND")}>Recommend</Button>
                            <Button size="xs" color="orange" variant="outline" onClick={() => handleUnitHeadAction(r.id, "NOT_RECOMMEND")}>Not Recommend</Button>
                          </>
                        )}
                        {r.status === "AWAITING_SANCTION_AUTHORITY_REVIEW" && (
                          <>
                            <Button size="xs" color="green" onClick={() => handleSanctionAction(r.id, "APPROVE")}>Sanction Approve</Button>
                            <Button size="xs" color="red" variant="outline" onClick={() => handleSanctionAction(r.id, "REJECT")}>Sanction Reject</Button>
                          </>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>

      {/* Record Offline Modal */}
      <Modal opened={offlineOpened} onClose={() => setOfflineOpened(false)} title="Record Offline-Sanctioned Leave" size="md">
        <Stack gap="md">
          <TextInput label="Employee ID" value={empId} onChange={(e) => setEmpId(e.target.value)} required />
          <Select
            label="Leave Category"
            value={cat}
            onChange={(val) => setCat(val || "CL")}
            data={[
              { value: "CL", label: "Casual Leave" },
              { value: "RH", label: "Restricted Holiday" },
              { value: "SCL", label: "Special Casual Leave" },
              { value: "EL", label: "Earned Leave" },
              { value: "VL", label: "Vacation Leave" },
              { value: "COL", label: "Commuted Leave" },
            ]}
          />
          <Group grow>
            <TextInput label="Start Date" type="date" value={sDate} onChange={(e) => setSDate(e.target.value)} required />
            <TextInput label="End Date" type="date" value={eDate} onChange={(e) => setEDate(e.target.value)} required />
          </Group>
          <TextInput label="Sanction Order / Reference Number" value={refNo} onChange={(e) => setRefNo(e.target.value)} required />
          <Textarea label="Sanction Reason / Remarks" value={offlineReason} onChange={(e) => setOfflineReason(e.target.value)} required />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOfflineOpened(false)}>Cancel</Button>
            <Button onClick={handleRecordOffline}>Record & Synchronize</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
