import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Stack, Table, Tabs, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaInbox, FaTimesCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useStudentRequestsOverview,
  useSubmitDeregistration,
  useSubmitRegistration,
} from "../api/hooks";

export default function MyRequestsPage() {
  const { data, isLoading, error } = useStudentRequestsOverview();
  const submitReg = useSubmitRegistration();
  const submitDereg = useSubmitDeregistration();

  const handleRegister = () => {
    submitReg.mutate(undefined, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Registration Submitted",
          message: "Your mess registration request has been submitted.",
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Registration Failed",
          message: errorMessage(err),
        });
      },
    });
  };

  const handleDeregister = () => {
    submitDereg.mutate(undefined, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Deregistration Submitted",
          message: "Your deregistration request has been submitted for caretaker review.",
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Deregistration Failed",
          message: errorMessage(err),
        });
      },
    });
  };

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="lg">
      <PageHeader title="My Requests" />
      <Stack gap="lg">
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            Manage your mess registration, deregistration, rebates, and special food requests.
          </Text>
          <Group>
            <Button onClick={handleRegister} loading={submitReg.isPending} color="blue">
              Register for Mess
            </Button>
            <Button onClick={handleDeregister} loading={submitDereg.isPending} color="red" variant="light">
              Request Deregistration
            </Button>
          </Group>
        </Group>

        <Tabs defaultValue="registrations">
          <Tabs.List>
            <Tabs.Tab value="registrations">
              Registrations ({data?.registrations?.length ?? 0})
            </Tabs.Tab>
            <Tabs.Tab value="deregistrations">
              Deregistrations ({data?.deregistrations?.length ?? 0})
            </Tabs.Tab>
            <Tabs.Tab value="rebates">Rebates ({data?.rebates?.length ?? 0})</Tabs.Tab>
            <Tabs.Tab value="special_food">
              Special Food ({data?.special_food?.length ?? 0})
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="registrations" pt="md">
            <Card withBorder>
              {isLoading ? (
                <Text c="dimmed">Loading...</Text>
              ) : !data?.registrations?.length ? (
                <Alert color="gray">No registration requests found.</Alert>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Submitted At</Table.Th>
                      <Table.Th>Decided At</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.registrations.map((r) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>#{r.id}</Table.Td>
                        <Table.Td>
                          <StatusBadge status={r.status} />
                        </Table.Td>
                        <Table.Td>{new Date(r.submitted_at).toLocaleDateString()}</Table.Td>
                        <Table.Td>
                          {r.decided_at ? new Date(r.decided_at).toLocaleDateString() : "—"}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="deregistrations" pt="md">
            <Card withBorder>
              {isLoading ? (
                <Text c="dimmed">Loading...</Text>
              ) : !data?.deregistrations?.length ? (
                <Alert color="gray">No deregistration requests found.</Alert>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Effective Date</Table.Th>
                      <Table.Th>Submitted At</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.deregistrations.map((d) => (
                      <Table.Tr key={d.id}>
                        <Table.Td>#{d.id}</Table.Td>
                        <Table.Td>
                          <StatusBadge status={d.status} />
                        </Table.Td>
                        <Table.Td>{d.effective_date || "Pending Next Calendar Day"}</Table.Td>
                        <Table.Td>{new Date(d.submitted_at).toLocaleDateString()}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="rebates" pt="md">
            <Card withBorder>
              {isLoading ? (
                <Text c="dimmed">Loading...</Text>
              ) : !data?.rebates?.length ? (
                <Alert color="gray">No rebate requests found.</Alert>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Reason</Table.Th>
                      <Table.Th>Requested Dates</Table.Th>
                      <Table.Th>Approved Dates</Table.Th>
                      <Table.Th>Status</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.rebates.map((rb) => (
                      <Table.Tr key={rb.id}>
                        <Table.Td>#{rb.id}</Table.Td>
                        <Table.Td>{rb.reason}</Table.Td>
                        <Table.Td>
                          {rb.start_date} to {rb.end_date}
                        </Table.Td>
                        <Table.Td>
                          {rb.approved_start_date
                            ? `${rb.approved_start_date} to ${rb.approved_end_date}`
                            : "—"}
                        </Table.Td>
                        <Table.Td>
                          <StatusBadge status={rb.status} />
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="special_food" pt="md">
            <Card withBorder>
              {isLoading ? (
                <Text c="dimmed">Loading...</Text>
              ) : !data?.special_food?.length ? (
                <Alert color="gray">No special food requests found.</Alert>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Reason</Table.Th>
                      <Table.Th>Status</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.special_food.map((sf) => (
                      <Table.Tr key={sf.id}>
                        <Table.Td>#{sf.id}</Table.Td>
                        <Table.Td>{sf.requested_date}</Table.Td>
                        <Table.Td>{sf.reason}</Table.Td>
                        <Table.Td>
                          <StatusBadge status={sf.status} />
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
