import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus, FaKey, FaHistory, FaSignOutAlt, FaExchangeAlt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useAccommodationRequests,
  useAllotments,
  useAllotRoom,
  useHostels,
  useReallotRoom,
  useRoomHistory,
  useRooms,
  useSubmitAccommodationRequest,
  useVacateRoom,
} from "../api/hooks";
import type { AccommodationRequest, RoomAllotment, RoomAssignmentHistory } from "../api/types";

export default function AllotmentManagementPage() {
  const { can } = useAuth();
  const { data: requests, isPending: requestsPending, error: reqError } = useAccommodationRequests();
  const { data: allotments, isPending: allotmentsPending } = useAllotments();
  const { data: history, isPending: historyPending } = useRoomHistory();
  const { data: hostels } = useHostels();
  const { data: rooms } = useRooms();

  const submitReq = useSubmitAccommodationRequest();
  const allotRoom = useAllotRoom();
  const reallotRoom = useReallotRoom();
  const vacateRoom = useVacateRoom();

  const [activeTab, setActiveTab] = useState<string | null>("requests");
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [allotModalOpen, setAllotModalOpen] = useState(false);
  const [reallotModalOpen, setReallotModalOpen] = useState(false);
  const [vacateModalOpen, setVacateModalOpen] = useState(false);

  // Selection states
  const [selectedReq, setSelectedReq] = useState<AccommodationRequest | null>(null);
  const [selectedAllot, setSelectedAllot] = useState<RoomAllotment | null>(null);

  // Forms
  const [appHostelId, setAppHostelId] = useState<string | null>(null);
  const [appYear, setAppYear] = useState("2026-2027");
  const [appSem, setAppSem] = useState("Monsoon");
  const [appReason, setAppReason] = useState("");

  const [targetRoomId, setTargetRoomId] = useState<string | null>(null);
  const [newRoomId, setNewRoomId] = useState<string | null>(null);
  const [reallotReason, setReallotReason] = useState("");
  const [vacateReasonText, setVacateReasonText] = useState("");

  if (reqError) {
    return (
      <Container size="xl">
        <ErrorState error={reqError} />
      </Container>
    );
  }

  const handleApply = async () => {
    await submitReq.mutateAsync({
      academic_year: appYear,
      semester: appSem,
      requested_hostel: appHostelId ? Number(appHostelId) : null,
      reason: appReason,
    });
    setApplyModalOpen(false);
    setAppReason("");
  };

  const handleAllot = async () => {
    if (!selectedReq || !targetRoomId) return;
    await allotRoom.mutateAsync({
      requestId: selectedReq.id,
      roomId: Number(targetRoomId),
    });
    setAllotModalOpen(false);
    setTargetRoomId(null);
  };

  const handleReallot = async () => {
    if (!selectedAllot || !newRoomId) return;
    await reallotRoom.mutateAsync({
      allotmentId: selectedAllot.id,
      newRoomId: Number(newRoomId),
      reason: reallotReason,
    });
    setReallotModalOpen(false);
    setNewRoomId(null);
    setReallotReason("");
  };

  const handleVacate = async () => {
    if (!selectedAllot) return;
    await vacateRoom.mutateAsync({
      allotmentId: selectedAllot.id,
      reason: vacateReasonText,
    });
    setVacateModalOpen(false);
    setVacateReasonText("");
  };

  const availableRooms = (rooms ?? [])
    .filter((r) => r.is_available && r.available_beds > 0)
    .map((r) => ({
      value: String(r.id),
      label: `${r.hostel_name} - Room ${r.room_number} (${r.available_beds} beds free)`,
    }));

  const hostelOptions = (hostels ?? []).map((h) => ({
    value: String(h.id),
    label: `${h.name} (${h.code})`,
  }));

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Accommodation & Allotment"
        subtitle="Manage student accommodation applications, batch room allotments, and occupancy lifecycle"
        action={
          can("hostel.accommodation.apply") && (
            <Button leftSection={<FaPlus size={12} />} onClick={() => setApplyModalOpen(true)}>
              Apply for Accommodation
            </Button>
          )
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} mb="lg">
        <Tabs.List>
          <Tabs.Tab value="requests" leftSection={<FaKey size={14} />}>
            Accommodation Requests ({requests?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="allotments" leftSection={<FaKey size={14} />}>
            Active Allotments ({allotments?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="history" leftSection={<FaHistory size={14} />}>
            Allocation History
          </Tabs.Tab>
        </Tabs.List>

        {/* REQUESTS TAB */}
        <Tabs.Panel value="requests" pt="md">
          <Card withBorder padding="md">
            <DataTable<AccommodationRequest>
              rows={requests ?? []}
              loading={requestsPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "roll", header: "Roll Number", render: (r) => <Text fw={600}>{r.student_roll_number}</Text> },
                { key: "name", header: "Student Name", render: (r) => r.student_name },
                { key: "year", header: "Academic Year", render: (r) => r.academic_year },
                { key: "semester", header: "Semester", render: (r) => r.semester },
                { key: "hostel", header: "Pref. Hostel", render: (r) => r.requested_hostel_name || "Any" },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Badge color={r.status === "allotted" ? "teal" : r.status === "submitted" ? "blue" : "gray"}>
                      {r.status.toUpperCase()}
                    </Badge>
                  ),
                },
                {
                  key: "action",
                  header: "Action",
                  render: (r) =>
                    can("hostel.allotment.manage") && r.status === "submitted" ? (
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => {
                          setSelectedReq(r);
                          setAllotModalOpen(true);
                        }}
                      >
                        Allot Room
                      </Button>
                    ) : null,
                },
              ]}
              empty={{
                title: "No Accommodation Requests",
                description: "Student hostel applications will appear here.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* ACTIVE ALLOTMENTS TAB */}
        <Tabs.Panel value="allotments" pt="md">
          <Card withBorder padding="md">
            <DataTable<RoomAllotment>
              rows={allotments ?? []}
              loading={allotmentsPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "hostel", header: "Hostel", render: (r) => r.hostel_name },
                { key: "room", header: "Room #", render: (r) => <Text fw={600}>{r.room_number}</Text> },
                { key: "roll", header: "Roll Number", render: (r) => r.student_roll_number },
                { key: "name", header: "Student Name", render: (r) => r.student_name },
                { key: "date", header: "Allotted Date", render: (r) => new Date(r.allotted_at).toLocaleDateString() },
                {
                  key: "actions",
                  header: "Actions",
                  render: (r) =>
                    can("hostel.allotment.manage") && (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          variant="light"
                          leftSection={<FaExchangeAlt size={10} />}
                          onClick={() => {
                            setSelectedAllot(r);
                            setReallotModalOpen(true);
                          }}
                        >
                          Re-allot
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="subtle"
                          leftSection={<FaSignOutAlt size={10} />}
                          onClick={() => {
                            setSelectedAllot(r);
                            setVacateModalOpen(true);
                          }}
                        >
                          Vacate
                        </Button>
                      </Group>
                    ),
                },
              ]}
              empty={{
                title: "No Active Allotments",
                description: "Allotted resident rooms will be displayed here.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* HISTORY TAB */}
        <Tabs.Panel value="history" pt="md">
          <Card withBorder padding="md">
            <DataTable<RoomAssignmentHistory>
              rows={history ?? []}
              loading={historyPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "roll", header: "Student Roll", render: (r) => r.student_roll_number },
                { key: "action", header: "Action", render: (r) => <Badge color="indigo">{r.action_type.toUpperCase()}</Badge> },
                { key: "from", header: "From Room", render: (r) => r.from_room_number || "None (New)" },
                { key: "to", header: "To Room", render: (r) => r.to_room_number || "None (Vacated)" },
                { key: "time", header: "Timestamp", render: (r) => new Date(r.timestamp).toLocaleString() },
                { key: "reason", header: "Reason", render: (r) => r.reason || "—" },
              ]}
              empty={{
                title: "No Assignment History",
                description: "Audit trail of student room allocations, exchanges, and vacations will be tracked here.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* APPLY ACCOMMODATION MODAL */}
      <Modal opened={applyModalOpen} onClose={() => setApplyModalOpen(false)} title="Apply for Hostel Accommodation">
        <Stack gap="sm">
          <TextInput label="Academic Year" required value={appYear} onChange={(e) => setAppYear(e.currentTarget.value)} />
          <TextInput label="Semester" required value={appSem} onChange={(e) => setAppSem(e.currentTarget.value)} />
          <Select
            label="Preferred Hostel (Optional)"
            placeholder="Select preferred hostel"
            data={hostelOptions}
            value={appHostelId}
            onChange={setAppHostelId}
            clearable
          />
          <Textarea label="Reason / Special Requirements" value={appReason} onChange={(e) => setAppReason(e.currentTarget.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setApplyModalOpen(false)}>Cancel</Button>
            <Button loading={submitReq.isPending} onClick={handleApply}>Submit Application</Button>
          </Group>
        </Stack>
      </Modal>

      {/* ALLOT ROOM MODAL */}
      <Modal opened={allotModalOpen} onClose={() => setAllotModalOpen(false)} title="Allot Room to Student">
        <Stack gap="sm">
          <Text size="sm">
            Allotting room for <b>{selectedReq?.student_name}</b> ({selectedReq?.student_roll_number})
          </Text>
          <Select
            label="Select Available Room"
            placeholder="Choose room with available bed"
            data={availableRooms}
            value={targetRoomId}
            onChange={setTargetRoomId}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAllotModalOpen(false)}>Cancel</Button>
            <Button loading={allotRoom.isPending} onClick={handleAllot} disabled={!targetRoomId}>
              Confirm Allotment
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* RE-ALLOT MODAL */}
      <Modal opened={reallotModalOpen} onClose={() => setReallotModalOpen(false)} title="Re-allot Student Room">
        <Stack gap="sm">
          <Text size="sm">
            Current Room: <b>{selectedAllot?.hostel_name} - {selectedAllot?.room_number}</b>
          </Text>
          <Select
            label="New Target Room"
            placeholder="Select destination room"
            data={availableRooms}
            value={newRoomId}
            onChange={setNewRoomId}
            required
          />
          <TextInput
            label="Re-allotment Reason"
            placeholder="e.g. Maintenance repair, medical request"
            value={reallotReason}
            onChange={(e) => setReallotReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setReallotModalOpen(false)}>Cancel</Button>
            <Button loading={reallotRoom.isPending} onClick={handleReallot} disabled={!newRoomId}>
              Confirm Transfer
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* VACATE MODAL */}
      <Modal opened={vacateModalOpen} onClose={() => setVacateModalOpen(false)} title="Record Room Vacation">
        <Stack gap="sm">
          <Text size="sm">
            Vacating room <b>{selectedAllot?.room_number}</b> for student <b>{selectedAllot?.student_name}</b>
          </Text>
          <TextInput
            label="Vacation Reason / Remarks"
            placeholder="e.g. Graduation, semester completion"
            value={vacateReasonText}
            onChange={(e) => setVacateReasonText(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setVacateModalOpen(false)}>Cancel</Button>
            <Button color="red" loading={vacateRoom.isPending} onClick={handleVacate}>
              Confirm Vacation
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
