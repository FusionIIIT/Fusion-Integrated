import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Loader,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  useApplyLeave,
  useCancelLeave,
  useLeaveBalances,
  useLeaveCatalog,
  useMyLeaveRequests,
  useWithdrawLeave,
} from "../api/hooks";

export default function LeavePage() {
  const catalog = useLeaveCatalog();
  const balances = useLeaveBalances();
  const requests = useMyLeaveRequests();
  const applyMutation = useApplyLeave();
  const withdrawMutation = useWithdrawLeave();
  const cancelMutation = useCancelLeave();

  const [category, setCategory] = useState<string>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [halfDay, setHalfDay] = useState<string | null>(null);
  const [purpose, setPurpose] = useState<string>("");
  const [isStationLeave, setIsStationLeave] = useState<boolean>(false);
  const [destination, setDestination] = useState<string>("");
  const [emergencyContact, setEmergencyContact] = useState<string>("");
  const [substituteId, setSubstituteId] = useState<string>("");

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    applyMutation.mutate({
      category,
      start_date: startDate,
      end_date: endDate,
      half_day: halfDay || undefined,
      purpose,
      is_station_leave: isStationLeave,
      destination: isStationLeave ? destination : undefined,
      emergency_contact: isStationLeave ? emergencyContact : undefined,
      substitute_id: substituteId ? parseInt(substituteId, 10) : undefined,
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "sanctioned":
        return <Badge color="green">Sanctioned</Badge>;
      case "under_review":
      case "recommended":
        return <Badge color="blue">Under Review</Badge>;
      case "awaiting_substitute":
        return <Badge color="yellow">Awaiting Substitute</Badge>;
      case "rejected":
        return <Badge color="red">Rejected</Badge>;
      case "withdrawn":
      case "cancelled":
        return <Badge color="gray">{status.toUpperCase()}</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  if (catalog.isLoading || balances.isLoading) return <Loader />;

  return (
    <Stack gap="lg">
      <Title order={2}>Employee Leave Management</Title>

      {/* Leave Balances Grid */}
      <Title order={4}>Current Leave Balances</Title>
      <SimpleGrid cols={{ base: 1, sm: 3, md: 6 }}>
        {balances.data?.map((b) => (
          <Card key={b.category} shadow="xs" padding="md" withBorder>
            <Text fw={600} size="sm">{b.category}</Text>
            <Title order={3}>{b.balance}</Title>
            <Text size="xs" c="dimmed">Credited: {b.credited} | Availed: {b.availed}</Text>
          </Card>
        ))}
      </SimpleGrid>

      {/* Apply Leave Form */}
      <Paper shadow="xs" p="md" withBorder>
        <Title order={4} mb="md">Apply for Leave</Title>
        <form onSubmit={handleApply}>
          <Stack gap="sm">
            <Group grow>
              <Select
                label="Leave Category"
                value={category}
                onChange={(val) => setCategory(val || "CL")}
                data={Object.keys(catalog.data?.entitlements || {}).map((c) => ({
                  value: c,
                  label: c,
                }))}
                required
              />
              <Select
                label="Half Day (CL only)"
                value={halfDay}
                onChange={setHalfDay}
                data={[
                  { value: "first", label: "First Half" },
                  { value: "second", label: "Second Half" },
                ]}
                clearable
              />
            </Group>

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
              <TextInput
                label="Substitute User ID (Optional)"
                type="number"
                value={substituteId}
                onChange={(e) => setSubstituteId(e.target.value)}
              />
            </Group>

            <Textarea
              label="Purpose / Reason"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              required
            />

            <Checkbox
              label="Station Leave Required"
              checked={isStationLeave}
              onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
            />

            {isStationLeave && (
              <Group grow>
                <TextInput
                  label="Destination"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  required
                />
                <TextInput
                  label="Emergency Contact"
                  value={emergencyContact}
                  onChange={(e) => setEmergencyContact(e.target.value)}
                  required
                />
              </Group>
            )}

            {applyMutation.isError && (
              <Alert color="red">Failed to submit leave request.</Alert>
            )}
            {applyMutation.isSuccess && (
              <Alert color="green">Leave request submitted successfully!</Alert>
            )}

            <Button type="submit" loading={applyMutation.isPending} mt="xs">
              Submit Application
            </Button>
          </Stack>
        </form>
      </Paper>

      {/* Leave Application History */}
      <Paper shadow="xs" p="md" withBorder>
        <Title order={4} mb="md">My Leave Applications</Title>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.data?.map((req) => (
              <Table.Tr key={req.id}>
                <Table.Td>{req.id}</Table.Td>
                <Table.Td>{req.category}</Table.Td>
                <Table.Td>{req.start_date} to {req.end_date}</Table.Td>
                <Table.Td>{req.leave_days}</Table.Td>
                <Table.Td>{getStatusBadge(req.status)}</Table.Td>
                <Table.Td>
                  {["submitted", "awaiting_substitute", "under_review", "recommended"].includes(req.status) && (
                    <Button
                      size="xs"
                      color="orange"
                      variant="light"
                      onClick={() => withdrawMutation.mutate(req.id)}
                    >
                      Withdraw
                    </Button>
                  )}
                  {req.status === "sanctioned" && (
                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      onClick={() => cancelMutation.mutate(req.id)}
                    >
                      Cancel
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
