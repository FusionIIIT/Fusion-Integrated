import { Button, Container, Group, Paper, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";
import { useDepartmentAction, useDepartmentFeed, useDepartmentRecord } from "./api";
import { useDepartmentCan } from "./DepartmentLayout";
import { FeedState } from "./FeedState";

interface Lab { id: number; name: string; details: string }
interface Details { department: string; official_name: string; general_information: string; core_policies: string }
interface Proposal { id: number; field: string; value: string; status: string }

export function LabsPage() {
  const can = useDepartmentCan();
  const feed = useDepartmentFeed<Lab>("labs");
  const action = useDepartmentAction();
  const [name, setName] = useState("");
  const [details, setDetails] = useState("");
  const canUpdate = can("department.lab.update");
  return (
    <Container size="md" py="lg">
      <PageHeader title="Lab resources" />
      <Stack>
        {canUpdate && (
          <Paper withBorder p="md" component="form" onSubmit={(event) => {
            event.preventDefault();
            action.mutate({ path: "labs", data: { name, details } }, {
              onSuccess: () => { setName(""); setDetails(""); },
            });
          }}>
            <Stack>
              <TextInput label="Lab name" required maxLength={160} value={name}
                onChange={(event) => setName(event.currentTarget.value)} />
              <Textarea label="Equipment and resource details" required maxLength={8000} value={details}
                onChange={(event) => setDetails(event.currentTarget.value)} />
              <Button type="submit" loading={action.isPending}>Save lab profile</Button>
              {action.isError && <ErrorState error={action.error} />}
            </Stack>
          </Paper>
        )}
        {feed.rows.map((lab) => (
          <Paper key={lab.id} withBorder p="md">
            <Group justify="space-between">
              <Text fw={600}>{lab.name}</Text>
              {canUpdate && <Button variant="default" onClick={() => { setName(lab.name); setDetails(lab.details); }}>Edit</Button>}
            </Group>
            <Text style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{lab.details}</Text>
          </Paper>
        ))}
        <FeedState query={feed} empty="There are no lab resource profiles." />
      </Stack>
    </Container>
  );
}

function GeneralDetailsForm({ details }: { details: Details }) {
  const [general, setGeneral] = useState(details.general_information);
  const action = useDepartmentAction();
  return (
    <form onSubmit={(event) => {
      event.preventDefault();
      action.mutate({ path: "details", data: { general_information: general } });
    }}>
      <Stack>
        <Textarea label="General information" maxLength={8000} value={general}
          onChange={(event) => setGeneral(event.currentTarget.value)} />
        <Button type="submit" loading={action.isPending}>Save general information</Button>
        {action.isSuccess && <Text role="status">General information saved.</Text>}
        {action.isError && <ErrorState error={action.error} />}
      </Stack>
    </form>
  );
}

export function DepartmentDetailsPage() {
  const can = useDepartmentCan();
  const details = useDepartmentRecord<Details>("details");
  const proposals = useDepartmentFeed<Proposal>("proposals");
  const action = useDepartmentAction();
  const [field, setField] = useState<string | null>("official_name");
  const [value, setValue] = useState("");
  const label = (name: string) => name === "official_name" ? "Official name" : "Core policies";

  return (
    <Container size="md" py="lg">
      <PageHeader title="Department details" />
      <Stack>
        {details.isError && <ErrorState error={details.error} />}
        {details.data && (
          <Paper withBorder p="md">
            <Stack>
              <Text fw={600}>{details.data.official_name || details.data.department}</Text>
              {details.data.core_policies && <Text style={{ whiteSpace: "pre-wrap" }}>{details.data.core_policies}</Text>}
              {can("department.details.update")
                ? <GeneralDetailsForm details={details.data} />
                : <Text style={{ whiteSpace: "pre-wrap" }}>{details.data.general_information}</Text>}
            </Stack>
          </Paper>
        )}
        {can("department.proposal.create") && (
          <Paper withBorder p="md" component="form" onSubmit={(event) => {
            event.preventDefault();
            action.mutate({ path: "proposals", data: { field, value } }, { onSuccess: () => setValue("") });
          }}>
            <Stack>
              <Select label="Official field" value={field} onChange={setField} allowDeselect={false}
                data={["official_name", "core_policies"].map((key) => ({ value: key, label: label(key) }))} />
              <Textarea label="Proposed value" required value={value} maxLength={field === "official_name" ? 200 : 8000}
                onChange={(event) => setValue(event.currentTarget.value)} />
              <Button type="submit" loading={action.isPending} disabled={!value.trim()}>Submit for approval</Button>
            </Stack>
          </Paper>
        )}
        {proposals.rows.map((proposal) => (
          <Paper key={proposal.id} withBorder p="md">
            <Stack>
              <Text fw={600}>{label(proposal.field)} · {proposal.status}</Text>
              <Text style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{proposal.value}</Text>
              {proposal.status === "pending" && can("department.proposal.approve") && (
                <Group>
                  {(["approve", "reject"] as const).map((decision) => (
                    <Button key={decision} disabled={action.isPending} onClick={() => action.mutate({
                      path: `proposals/${proposal.id}/action`, data: { action: decision },
                    })}>{decision === "approve" ? "Approve" : "Reject"}</Button>
                  ))}
                </Group>
              )}
            </Stack>
          </Paper>
        ))}
        {action.isError && <ErrorState error={action.error} />}
        <FeedState query={proposals} empty="There are no official change proposals." />
      </Stack>
    </Container>
  );
}
