import {
  Alert, Button, Card, Checkbox, Group, Select, SimpleGrid, Stack, Table,
  Text, TextInput, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";

import { errorMessage } from "../../../lib/http";
import {
  useExportLeaveRequest, useLeaveAction, useLeaveBalances, useMyLeaveRequests,
  useSubmitLeave,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import "./LeaveRequestsPage.css";

const CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"];

export default function LeaveRequestsPage() {
  const balances = useLeaveBalances();
  const requests = useMyLeaveRequests();
  const submit = useSubmitLeave();
  const withdraw = useLeaveAction("withdraw");
  const exportRequest = useExportLeaveRequest();
  const [printRequest, setPrintRequest] = useState<LeaveRequest | null>(null);
  const [category, setCategory] = useState<string | null>("CL");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [purpose, setPurpose] = useState("");
  const [halfDayPart, setHalfDayPart] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationDestination, setStationDestination] = useState("");
  const [stationContact, setStationContact] = useState("");
  const [medicalEvidence, setMedicalEvidence] = useState("");
  const [substituteUserId, setSubstituteUserId] = useState("");

  const fail = (error: unknown) =>
    notifications.show({ color: "red", message: errorMessage(error) });

  useEffect(() => {
    if (!printRequest) return;
    window.print();
    setPrintRequest(null);
  }, [printRequest]);

  const createRequest = () => {
    if (!category || !startsOn || !endsOn || !purpose.trim()
      || (stationLeave && !stationDestination.trim())
      || (substituteUserId && (!Number.isInteger(Number(substituteUserId))
        || Number(substituteUserId) <= 0))) {
      notifications.show({ color: "red", message: "Complete every required field." });
      return;
    }
    submit.mutate(
      {
        category,
        starts_on: startsOn,
        ends_on: endsOn,
        purpose,
        half_day_part: category === "CL" ? halfDayPart : "",
        station_leave: stationLeave,
        station_destination: stationDestination,
        station_contact: stationContact,
        medical_evidence: medicalEvidence,
        ...(substituteUserId ? { substitute_user_id: Number(substituteUserId) } : {}),
      },
      {
        onError: fail,
        onSuccess: () => {
          setPurpose("");
          notifications.show({ message: "Leave request submitted." });
        },
      },
    );
  };

  return (
    <>
    <Stack className="elm-screen-content">
      <Title order={2}>My Leave</Title>
      {(balances.isError || requests.isError) && (
        <Alert color="red" title="Unable to load leave information">
          {errorMessage(balances.error ?? requests.error)}
        </Alert>
      )}
      <Title order={3}>Current balances</Title>
      {balances.data && (
        <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }}>
          {balances.data.map((balance) => (
            <Card key={`${balance.category}-${balance.year}`} withBorder>
              <Text fw={700}>{balance.category}</Text>
              <Text size="sm">{balance.balance} days available</Text>
            </Card>
          ))}
        </SimpleGrid>
      )}
      <Card withBorder>
        <Stack>
          <Title order={3}>Apply for leave</Title>
          <Select
            label="Leave category"
            data={CATEGORIES}
            value={category}
            onChange={(value) => {
              setCategory(value);
              if (value !== "CL") setHalfDayPart("");
            }}
            required
          />
          <Group grow>
            <TextInput
              label="Start date"
              type="date"
              value={startsOn}
              onChange={(event) => setStartsOn(event.currentTarget.value)}
              required
            />
            <TextInput
              label="End date"
              type="date"
              value={endsOn}
              onChange={(event) => setEndsOn(event.currentTarget.value)}
              required
            />
          </Group>
          <TextInput
            label="Purpose / reason"
            value={purpose}
            onChange={(event) => setPurpose(event.currentTarget.value)}
            required
          />
          {category === "CL" && (
            <Select
              label="Half-day CL"
              placeholder="Full day"
              clearable
              data={[
                { value: "first_half", label: "First half" },
                { value: "second_half", label: "Second half" },
              ]}
              value={halfDayPart || null}
              onChange={(value) => setHalfDayPart(value ?? "")}
            />
          )}
          <Checkbox
            label="Include Station Leave details"
            checked={stationLeave}
            onChange={(event) => setStationLeave(event.currentTarget.checked)}
          />
          {stationLeave && (
            <Group grow>
              <TextInput
                label="Station Leave destination"
                value={stationDestination}
                onChange={(event) => setStationDestination(event.currentTarget.value)}
                required
              />
              <TextInput
                label="Contact during leave"
                value={stationContact}
                onChange={(event) => setStationContact(event.currentTarget.value)}
              />
            </Group>
          )}
          <Textarea
            label="Medical evidence (where applicable)"
            value={medicalEvidence}
            onChange={(event) => setMedicalEvidence(event.currentTarget.value)}
          />
          <TextInput
            label="Substitute employee user ID (when required)"
            inputMode="numeric"
            value={substituteUserId}
            onChange={(event) => setSubstituteUserId(event.currentTarget.value)}
          />
          <Button onClick={createRequest} loading={submit.isPending}>
            Submit request
          </Button>
        </Stack>
      </Card>
      <Title order={3}>Request history</Title>
      {requests.data && (
        <Table.ScrollContainer minWidth={700}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.data.results.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>{item.category}</Table.Td>
                  <Table.Td>{item.starts_on} – {item.ends_on}</Table.Td>
                  <Table.Td>{item.requested_days}</Table.Td>
                  <Table.Td>{item.status.replaceAll("_", " ")}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => setPrintRequest(item)}
                      >
                        Print
                      </Button>
                      <Button
                        size="xs"
                        variant="light"
                        loading={exportRequest.isPending}
                        onClick={() => exportRequest.mutate(item.id, { onError: fail })}
                      >
                        Export
                      </Button>
                      {["pending", "substitute_pending", "applicant_action_required"]
                        .includes(item.status) && (
                        <Button
                          size="xs"
                          variant="light"
                          loading={withdraw.isPending}
                          onClick={() => withdraw.mutate(
                            { id: item.id },
                            {
                              onError: fail,
                              onSuccess: () =>
                                notifications.show({ message: "Request withdrawn." }),
                            },
                          )}
                        >
                          Withdraw
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
    {printRequest && (
      <article className="elm-print-document">
        <h1>Employee Leave Application</h1>
        <p><strong>Request ID:</strong> {printRequest.id}</p>
        <p><strong>Employee ID:</strong> {printRequest.applicant_user_id}</p>
        <p><strong>Category:</strong> {printRequest.category}</p>
        <p><strong>Period:</strong> {printRequest.starts_on} to {printRequest.ends_on}</p>
        <p><strong>Requested days:</strong> {printRequest.requested_days}</p>
        <p><strong>Purpose:</strong> {printRequest.purpose}</p>
        <p><strong>Status:</strong> {printRequest.status.replaceAll("_", " ")}</p>
        <p><strong>Submitted:</strong> {printRequest.submitted_at ?? "—"}</p>
        <p><strong>Decision:</strong> {printRequest.decision_note || "—"}</p>
      </article>
    )}
    </>
  );
}
