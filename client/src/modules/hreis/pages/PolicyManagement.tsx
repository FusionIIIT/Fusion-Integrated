import { useState } from "react";
import {
  Alert, Button, Card, Divider, Group, Select, Stack, Table, Text,
  Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { useCreatePolicy, usePolicies } from "../api/hooks";
import type { HRPolicyInput } from "../api/types";

export function PolicyManagement() {
  const { can } = useAuth();
  const policies = usePolicies(can("hreis.policy.view"));
  const create = useCreatePolicy();
  const [expanded, setExpanded] = useState(false);
  const [family, setFamily] = useState<HRPolicyInput["family"]>("leave");
  const [version, setVersion] = useState("1");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [parameters, setParameters] = useState("{}");

  if (!can("hreis.policy.view")) return null;

  function save() {
    try {
      const config: unknown = JSON.parse(parameters);
      if (!config || typeof config !== "object" || Array.isArray(config)) {
        throw new Error("Policy parameters must be a JSON object.");
      }
      const effective_from = new Date(start).toISOString();
      const effective_until = end.trim() ? new Date(end).toISOString() : null;
      const next = Number(version);
      if (!Number.isInteger(next) || next <= 0) {
        throw new Error("Policy version must be a positive integer.");
      }
      create.mutate({
        family, version: next, effective_from, effective_until,
        parameters: config as Record<string, unknown>,
      }, {
        onSuccess: () => {
          notifications.show({ position: "top-center", color: "green", title: "Policy version recorded",
            message: "The version is immutable and has an audit entry." });
          setExpanded(false);
        },
        onError: (error) => notifications.show({ position: "top-center",
          color: "red", title: "Could not record HR policy",
          message: errorMessage(error),
        }),
      });
    } catch (error) {
      notifications.show({ position: "top-center", color: "red", title: "Invalid policy input",
        message: error instanceof Error ? error.message : "Check policy values." });
    }
  }

  return (
    <Stack mt="xl">
      <Divider label="Institutional policy versions" labelPosition="left" />
      <Alert color="yellow" title="No assumed policy defaults">
        Only enter institutionally approved leave eligibility, department-specific
        approval routes, and appraisal windows. Unspecified financial criteria,
        quotas and authority mappings remain blocked.
      </Alert>
      {policies.error && <Text c="red" size="sm">
        Could not load the current policy versions: {errorMessage(policies.error)}
      </Text>}
      {policies.isPending && <Text c="dimmed">Loading policy versions...</Text>}
      {policies.data && <Card withBorder>
        {policies.data.results.length === 0 ? <Text c="dimmed">
          No policy versions are configured. Request submissions requiring policy
          values will be refused.
        </Text> : <Table.ScrollContainer minWidth={560}><Table>
          <Table.Thead><Table.Tr>
            <Table.Th>Family</Table.Th>
            <Table.Th>Version</Table.Th>
            <Table.Th>Effective</Table.Th>
            <Table.Th>Until</Table.Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody>{policies.data.results.map((item) => (
            <Table.Tr key={item.id}>
              <Table.Td>{item.family.toUpperCase()}</Table.Td>
              <Table.Td>{item.version}</Table.Td>
              <Table.Td>{new Date(item.effective_from).toLocaleDateString()}</Table.Td>
              <Table.Td>{item.effective_until
                ? new Date(item.effective_until).toLocaleDateString() : "Open-ended"}</Table.Td>
            </Table.Tr>
          ))}</Table.Tbody>
        </Table></Table.ScrollContainer>}
      </Card>}
      {can("hreis.policy.manage") && <>
        <Group><Button variant="light" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Close policy editor" : "Record new policy version"}
        </Button></Group>
        {expanded && <Card withBorder>
          <Stack>
            <Select label="Policy family" required value={family}
              data={["leave", "appraisal", "ltc", "cpda"]}
              onChange={(value) => setFamily(
                value === "appraisal" || value === "ltc" || value === "cpda"
                  ? value : "leave")} />
            <TextInput label="Policy version" required value={version}
              onChange={(event) => setVersion(event.currentTarget.value)} />
            <TextInput label="Effective from (ISO 8601 date and time with offset)"
              required placeholder="2026-12-01T00:00:00+05:30" value={start}
              onChange={(event) => setStart(event.currentTarget.value)} />
            <TextInput label="Effective until (optional)" value={end}
              placeholder="2027-12-01T00:00:00+05:30"
              onChange={(event) => setEnd(event.currentTarget.value)} />
            <Textarea label="Approved policy parameters (JSON)" autosize minRows={8}
              required value={parameters}
              onChange={(event) => setParameters(event.currentTarget.value)} />
            <Button loading={create.isPending} onClick={save}>
              Record immutable policy version
            </Button>
          </Stack>
        </Card>}
      </>}
    </Stack>
  );
}
