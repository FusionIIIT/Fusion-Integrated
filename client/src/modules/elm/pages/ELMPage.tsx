import { useState, useEffect } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import type { LeaveAccount, LeaveRequest } from "../api/types";

export default function ELMPage() {
  const [balances, setBalances] = useState<LeaveAccount[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [applyOpened, setApplyOpened] = useState(false);

  // Form state
  const [category, setCategory] = useState<string>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayType, setHalfDayType] = useState<string>("first_half");
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");

  const fetchBalances = async () => {
    try {
      const res = await fetch("/api/v1/elm/balances/");
      if (res.ok) {
        const data = await res.json();
        setBalances(data);
      }
    } catch {
      // fallback
    }
  };

  const fetchRequests = async () => {
    try {
      const res = await fetch("/api/v1/elm/requests/");
      if (res.ok) {
        const data = await res.json();
        setRequests(data);
      }
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    fetchBalances();
    fetchRequests();
  }, []);

  const handleApply = async () => {
    setLoading(true);
    try {
      const payload = {
        category,
        start_date: startDate,
        end_date: endDate,
        reason,
        substitute_id: substituteId ? parseInt(substituteId, 10) : null,
        is_half_day: isHalfDay,
        half_day_type: isHalfDay ? halfDayType : null,
        is_station_leave: isStationLeave,
        station_address: stationAddress,
        emergency_contact: emergencyContact,
      };

      const res = await fetch("/api/v1/elm/requests/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || JSON.stringify(err));
      }

      notifications.show({
        title: "Success",
        message: "Leave application submitted successfully.",
        color: "green",
      });
      setApplyOpened(false);
      fetchBalances();
      fetchRequests();
    } catch (err: any) {
      notifications.show({
        title: "Application Failed",
        message: err.message || "Failed to submit leave application.",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/elm/requests/${id}/withdraw/`, { method: "POST" });
      if (res.ok) {
        notifications.show({ title: "Withdrawn", message: "Leave request withdrawn.", color: "gray" });
        fetchBalances();
        fetchRequests();
      }
    } catch {
      notifications.show({ title: "Error", message: "Could not withdraw leave.", color: "red" });
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="xl">
        <Group justify="space-between">
          <div>
            <Title order={2}>Employee Leave Management</Title>
            <Text c="dimmed">View balances, apply for leave, and manage active requests.</Text>
          </div>
          <Button onClick={() => setApplyOpened(true)}>Apply for Leave</Button>
        </Group>

        {/* Leave Balances Grid */}
        <Title order={3}>Current Entitlement & Balances</Title>
        <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }}>
          {balances.map((b) => (
            <Card key={b.category} shadow="sm" padding="md" radius="md" withBorder>
              <Text fw={700} size="lg">{b.category}</Text>
              <Text size="sm" c="dimmed">Allotted: {b.allotted}</Text>
              <Text size="sm" c="dimmed">Used: {b.used}</Text>
              <Text size="sm" c="dimmed">Pending: {b.pending}</Text>
              <Text fw={600} size="md" c="blue" mt="xs">Available: {b.available}</Text>
            </Card>
          ))}
        </SimpleGrid>

        {/* Leave Requests Table */}
        <Title order={3}>My Leave Applications</Title>
        <Card shadow="sm" radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>From</Table.Th>
                <Table.Th>To</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    No leave requests found.
                  </Table.Td>
                </Table.Tr>
              ) : (
                requests.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td><Badge>{r.category}</Badge></Table.Td>
                    <Table.Td>{r.start_date}</Table.Td>
                    <Table.Td>{r.end_date}</Table.Td>
                    <Table.Td>{r.duration_days}</Table.Td>
                    <Table.Td><Badge color={r.status === "APPROVED" ? "green" : r.status === "REJECTED" ? "red" : "yellow"}>{r.status}</Badge></Table.Td>
                    <Table.Td>
                      {["AWAITING_SUBSTITUTE_RESPONSE", "AWAITING_UNIT_HEAD_REVIEW", "AWAITING_ESTABLISHMENT_REVIEW", "AWAITING_SANCTION_AUTHORITY_REVIEW"].includes(r.status) && (
                        <Button size="xs" variant="outline" color="red" onClick={() => handleWithdraw(r.id)}>
                          Withdraw
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>

      {/* Apply Leave Modal */}
      <Modal opened={applyOpened} onClose={() => setApplyOpened(false)} title="Apply for Leave" size="lg">
        <Stack gap="md">
          <Select
            label="Leave Category"
            value={category}
            onChange={(val) => setCategory(val || "CL")}
            data={[
              { value: "CL", label: "Casual Leave (CL)" },
              { value: "RH", label: "Restricted Holiday (RH)" },
              { value: "SCL", label: "Special Casual Leave (SCL)" },
              { value: "EL", label: "Earned Leave (EL)" },
              { value: "VL", label: "Vacation Leave (VL)" },
              { value: "COL", label: "Commuted Leave (COL)" },
            ]}
          />
          <Group grow>
            <TextInput label="Start Date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
            <TextInput label="End Date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
          </Group>

          {category === "CL" && (
            <Group>
              <Checkbox label="Half-day CL" checked={isHalfDay} onChange={(e) => setIsHalfDay(e.currentTarget.checked)} />
              {isHalfDay && (
                <Select
                  value={halfDayType}
                  onChange={(val) => setHalfDayType(val || "first_half")}
                  data={[
                    { value: "first_half", label: "First Half" },
                    { value: "second_half", label: "Second Half" },
                  ]}
                />
              )}
            </Group>
          )}

          <TextInput label="Nominated Substitute Employee ID (optional)" value={substituteId} onChange={(e) => setSubstituteId(e.target.value)} placeholder="e.g. 102" />
          <Textarea label="Purpose / Reason" value={reason} onChange={(e) => setReason(e.target.value)} required />

          <Checkbox label="Permission required for Station Leave (leaving Jabalpur)" checked={isStationLeave} onChange={(e) => setIsStationLeave(e.currentTarget.checked)} />
          {isStationLeave && (
            <Stack gap="xs">
              <TextInput label="Destination / Outstation Address" value={stationAddress} onChange={(e) => setStationAddress(e.target.value)} />
              <TextInput label="Emergency Contact Number" value={emergencyContact} onChange={(e) => setEmergencyContact(e.target.value)} />
            </Stack>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setApplyOpened(false)}>Cancel</Button>
            <Button loading={loading} onClick={handleApply}>Submit Application</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
