import { useEffect, useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDepartmentChangeAction, useDepartmentDetails, useProposeOfficialChange,
  useUpdateGeneralDetails,
} from "../api/hooks";

export default function DepartmentDetailsPage() {
  const { can } = useAuth();
  const details = useDepartmentDetails();
  const updateGeneral = useUpdateGeneralDetails();
  const propose = useProposeOfficialChange();
  const decide = useDepartmentChangeAction();
  const canManage = can("department.details.manage");
  const canApprove = can("department.details.approve");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fieldName, setFieldName] = useState("name");
  const [proposedValue, setProposedValue] = useState("");

  useEffect(() => {
    setName(String(details.data?.general.name ?? ""));
    setDescription(String(details.data?.general.description ?? ""));
  }, [details.data]);

  if (details.error) return <Container size="md"><ErrorState error={details.error} /></Container>;
  const changes = details.data?.changes ?? [];

  return (
    <Container size="md">
      <PageHeader title="Department details"
        subtitle="General information is editable by Dept_Admin; official changes require HOD approval." />
      <Stack gap="lg">
        <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>General information</Text>
            <TextInput label="Department name" value={name} readOnly={!canManage}
              onChange={(e) => setName(e.currentTarget.value)} />
            <TextInput label="Description and programme information" value={description}
              readOnly={!canManage}
              onChange={(e) => setDescription(e.currentTarget.value)} />
            {canManage && <Button w="fit-content" loading={updateGeneral.isPending}
              onClick={() => updateGeneral.mutate({ general: {
                name, description,
              } }, { onError: (e) => notifications.show({
                color: "red", title: "Could not save details", message: errorMessage(e),
              }) })}>Save general details</Button>}
          </Stack>
        </Card>

        <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>Approved official details</Text>
            {Object.entries(details.data?.official ?? {}).length === 0
              ? <Text c="dimmed">No official details have been set.</Text>
              : Object.entries(details.data?.official ?? {}).map(([key, value]) => (
                <Group key={key}><Badge variant="light">{key}</Badge><Text>{String(value)}</Text></Group>
              ))}
          </Stack>
        </Card>

        {canManage && (
          <Card withBorder padding="lg">
            <Stack>
              <Text fw={700}>Propose an official change</Text>
              <Text size="sm" c="dimmed">It remains pending until the HOD decides. Headship comes from central role assignment.</Text>
              <Group grow>
                <TextInput label="Official field" value={fieldName}
                  onChange={(e) => setFieldName(e.currentTarget.value)} />
                <TextInput label="Proposed value" value={proposedValue}
                  onChange={(e) => setProposedValue(e.currentTarget.value)} />
              </Group>
              <Button w="fit-content" disabled={!fieldName.trim() || !proposedValue.trim()}
                loading={propose.isPending}
                onClick={() => propose.mutate({ field_name: fieldName,
                  proposed_value: proposedValue,
                }, { onSuccess: () => setProposedValue(""), onError: (e) => notifications.show({
                  color: "red", title: "Could not propose change", message: errorMessage(e),
                }) })}>Submit for HOD approval</Button>
            </Stack>
          </Card>
        )}

        <section>
          <Text fw={700} mb="sm">Pending official changes</Text>
          {details.isPending ? <Text c="dimmed">Loading changes…</Text>
            : changes.length === 0 ? <Text c="dimmed">No pending changes.</Text>
              : <Stack gap="sm">{changes.map((change) => (
                <Card key={change.id} withBorder padding="md">
                  <Group justify="space-between">
                    <Stack gap={3}>
                      <Text fw={600}>{change.field_name}</Text>
                      <Text>{String(change.proposed_value)}</Text>
                      <Badge w="fit-content" variant="light">{change.status.replaceAll("_", " ")}</Badge>
                    </Stack>
                    {canApprove && <Group>
                      <Button size="xs" loading={decide.isPending}
                        onClick={() => decide.mutate({ id: change.id, action: "approve" }, {
                          onError: (e) => notifications.show({
                            color: "red", title: "Could not approve change", message: errorMessage(e),
                          }),
                        })}>Approve</Button>
                      <Button size="xs" variant="light" color="red" loading={decide.isPending}
                        onClick={() => decide.mutate({ id: change.id, action: "reject" }, {
                          onError: (e) => notifications.show({
                            color: "red", title: "Could not reject change", message: errorMessage(e),
                          }),
                        })}>Reject</Button>
                    </Group>}
                  </Group>
                </Card>
              ))}</Stack>}
        </section>
      </Stack>
    </Container>
  );
}
