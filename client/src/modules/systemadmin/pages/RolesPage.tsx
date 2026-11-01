import { useState } from "react";
import {
  Stack,
  Table,
  Badge,
  Text,
  Button,
  Paper,
  Group,
  Loader,
  Alert,
  Tooltip,
} from "@mantine/core";
import { FaUserPlus, FaExclamationTriangle } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRoles } from "../api/hooks";
import { AssignRoleModal } from "../components/RoleModals";

export default function RolesPage() {
  const { data, isLoading, error } = useRoles();
  const [assignOpen, setAssignOpen] = useState(false);

  return (
    <Stack gap="lg">
      <PageHeader
        title="Role Definition Directory"
        subtitle="Catalogue of institutional administrative roles, singularity rules, and conflict constraints"
        action={
          <Button
            leftSection={<FaUserPlus size={14} />}
            onClick={() => setAssignOpen(true)}
            disabled={!data || data.results.length === 0}
          >
            Assign Role
          </Button>
        }
      />

      {isLoading && (
        <Stack align="center" justify="center" p="xl">
          <Loader />
          <Text c="dimmed">Loading role catalogue...</Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error">
          Failed to load role definitions.
        </Alert>
      )}

      {data && (
        <Paper withBorder radius="md">
          <Table verticalSpacing="sm" striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Code</Table.Th>
                <Table.Th>Role Title</Table.Th>
                <Table.Th>Department / Scope</Table.Th>
                <Table.Th>Eligible Types</Table.Th>
                <Table.Th>Nature</Table.Th>
                <Table.Th>Current Status / Holder</Table.Th>
                <Table.Th>SoD Conflicts</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.results.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>
                    <Badge variant="outline">{r.code}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={600}>{r.name}</Text>
                    <Text size="xs" c="dimmed">{r.description}</Text>
                  </Table.Td>
                  <Table.Td>{r.module_or_dept || "Institute-wide"}</Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      {r.allowed_user_types.map((t) => (
                        <Badge key={t} size="xs" variant="light" color="cyan">
                          {t}
                        </Badge>
                      ))}
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Stack gap={2}>
                      <Badge size="xs" color={r.is_singular ? "violet" : "blue"} variant="light">
                        {r.is_singular ? "Singular (1 Holder)" : "Multi-Holder"}
                      </Badge>
                      {r.is_time_bound && (
                        <Badge size="xs" color="gray" variant="dot">
                          {r.default_validity_days ? `${r.default_validity_days} days` : "Time-bound"}
                        </Badge>
                      )}
                    </Stack>
                  </Table.Td>
                  <Table.Td>
                    {r.is_singular ? (
                      r.is_vacant ? (
                        <Badge color="red" leftSection={<FaExclamationTriangle size={10} />}>
                          VACANT
                        </Badge>
                      ) : r.current_holder ? (
                        <Stack gap={2}>
                          <Text size="xs" fw={600}>{r.current_holder.full_name}</Text>
                          <Text size="xs" c="dimmed">{r.current_holder.institute_id}</Text>
                        </Stack>
                      ) : (
                        <Text size="xs" c="dimmed">No active holder</Text>
                      )
                    ) : (
                      <Badge color="green" variant="light">
                        {r.active_holders_count ?? 0} active holder(s)
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {r.conflicts.length === 0 ? (
                      <Text size="xs" c="dimmed">None</Text>
                    ) : (
                      <Group gap={4}>
                        {r.conflicts.map((c) => (
                          <Tooltip key={c.id} label={c.reason}>
                            <Badge size="xs" color="pink" variant="outline">
                              ≠ {c.conflicting_role_code}
                            </Badge>
                          </Tooltip>
                        ))}
                      </Group>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      {data && (
        <AssignRoleModal
          roles={data.results}
          opened={assignOpen}
          onClose={() => setAssignOpen(false)}
        />
      )}
    </Stack>
  );
}
