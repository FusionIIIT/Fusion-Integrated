import { useState } from "react";
import { Badge, Button, Container, Tabs, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBan, FaMapMarkedAlt, FaScroll, FaUserCog } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useBlacklistVersions, usePolicies, usePublishBlacklist, usePublishPolicy, useRevokeRole,
  useRoles, useZones,
} from "../api/hooks";
import type { BlacklistVersion, Policy, RoleAssignment, Zone } from "../api/types";
import { formatDateTime, humanise } from "../format";

const STATUS_COLOR: Record<string, string> = {
  published: "green", draft: "yellow", archived: "gray", active: "green",
};

function Status({ value }: { value: string }) {
  return <Badge color={STATUS_COLOR[value] ?? "gray"} variant="light">{humanise(value)}</Badge>;
}

function fail(e: unknown) {
  notifications.show({ color: "red", message: errorMessage(e) });
}

function PoliciesTab() {
  const { can } = useAuth();
  const { data, isPending, error } = usePolicies();
  const publish = usePublishPolicy();
  if (error) return <ErrorState error={error} />;
  return (
    <DataTable<Policy>
      rows={data ?? []} loading={isPending} rowKey={(p) => p.id} minWidth={640}
      empty={{ title: "No policies yet" }}
      columns={[
        { key: "v", header: "Version", render: (p) => `v${p.version}` },
        { key: "s", header: "Status", render: (p) => <Status value={p.status} /> },
        { key: "h", header: "Visiting hours", render: (p) =>
          `${p.visiting_hours_start.slice(0, 5)} – ${p.visiting_hours_end.slice(0, 5)}` },
        { key: "m", header: "Max visit", render: (p) => `${p.max_visit_hours} h` },
        { key: "p", header: "Published", render: (p) => formatDateTime(p.published_at) },
        { key: "a", header: "", align: "right", render: (p) => (
          p.status === "draft" && can("vms.policy.publish") ? (
            <Button size="compact-xs" loading={publish.isPending && publish.variables === p.id}
              onClick={() => publish.mutate(p.id, {
                onSuccess: () => notifications.show({
                  color: "green", message: `Policy v${p.version} is now live.` }),
                onError: fail,
              })}>
              Publish
            </Button>
          ) : null
        ) },
      ]}
    />
  );
}

function BlacklistTab() {
  const { can } = useAuth();
  const { data, isPending, error } = useBlacklistVersions();
  const publish = usePublishBlacklist();
  if (error) return <ErrorState error={error} />;
  return (
    <DataTable<BlacklistVersion>
      rows={data ?? []} loading={isPending} rowKey={(v) => v.id} minWidth={520}
      empty={{ title: "No blacklist versions yet" }}
      columns={[
        { key: "v", header: "Version", render: (v) => `v${v.version}` },
        { key: "s", header: "Status", render: (v) => <Status value={v.status} /> },
        { key: "p", header: "Published", render: (v) => formatDateTime(v.published_at) },
        { key: "a", header: "", align: "right", render: (v) => (
          v.status === "draft" && can("vms.blacklist.publish") ? (
            <Button size="compact-xs" loading={publish.isPending && publish.variables === v.id}
              onClick={() => publish.mutate(v.id, {
                onSuccess: () => notifications.show({
                  color: "green", message: `Blacklist v${v.version} is now live.` }),
                onError: fail,
              })}>
              Publish
            </Button>
          ) : null
        ) },
      ]}
    />
  );
}

function RolesTab() {
  const { can } = useAuth();
  const { data, isPending, error } = useRoles();
  const revoke = useRevokeRole();
  if (error) return <ErrorState error={error} />;
  const live = (data ?? []).filter((r) => !r.revoked_at);
  return (
    <DataTable<RoleAssignment>
      rows={live} loading={isPending} rowKey={(r) => r.id} minWidth={640}
      empty={{ title: "No active role assignments" }}
      columns={[
        { key: "u", header: "User", render: (r) => `User ${r.user_id}` },
        { key: "r", header: "Role", render: (r) => humanise(r.role) },
        { key: "s", header: "Scope", render: (r) =>
          r.scope_type === "campus" ? "Campus" : `${humanise(r.scope_type)} ${r.scope_id}` },
        { key: "e", header: "Ends", render: (r) => formatDateTime(r.ends_at) },
        { key: "a", header: "", align: "right", render: (r) => (
          can("vms.role.assign") ? (
            <Button size="compact-xs" color="red" variant="light"
              loading={revoke.isPending && revoke.variables === r.id}
              onClick={() => revoke.mutate(r.id, {
                onSuccess: () => notifications.show({ color: "green", message: "Role revoked." }),
                onError: fail,
              })}>
              Revoke
            </Button>
          ) : null
        ) },
      ]}
    />
  );
}

function ZonesTab() {
  const { data, isPending, error } = useZones();
  if (error) return <ErrorState error={error} />;
  return (
    <DataTable<Zone>
      rows={data ?? []} loading={isPending} rowKey={(z) => z.id} minWidth={480}
      empty={{ title: "No zones yet" }}
      columns={[
        { key: "n", header: "Zone", render: (z) => z.name },
        { key: "r", header: "Access", render: (z) => (
          z.is_restricted ? <Badge color="orange" variant="light">Restricted</Badge>
            : <Text size="sm">Open</Text>
        ) },
        { key: "a", header: "Status", render: (z) => <Status value={z.is_active ? "active" : "archived"} /> },
      ]}
    />
  );
}

export default function AdminPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState<string | null>("policies");
  return (
    <Container size="lg">
      <PageHeader title="Administration"
        subtitle="Access policies, the blacklist, roles and campus zones" />
      <Tabs value={tab} onChange={setTab} keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="policies" leftSection={<FaScroll size={12} />}>Policies</Tabs.Tab>
          {can("vms.blacklist.manage") && (
            <Tabs.Tab value="blacklist" leftSection={<FaBan size={12} />}>Blacklist</Tabs.Tab>
          )}
          {can("vms.role.assign") && (
            <Tabs.Tab value="roles" leftSection={<FaUserCog size={12} />}>Roles</Tabs.Tab>
          )}
          {can("vms.zone.manage") && (
            <Tabs.Tab value="zones" leftSection={<FaMapMarkedAlt size={12} />}>Zones</Tabs.Tab>
          )}
        </Tabs.List>
        <Tabs.Panel value="policies"><PoliciesTab /></Tabs.Panel>
        <Tabs.Panel value="blacklist"><BlacklistTab /></Tabs.Panel>
        <Tabs.Panel value="roles"><RolesTab /></Tabs.Panel>
        <Tabs.Panel value="zones"><ZonesTab /></Tabs.Panel>
      </Tabs>
    </Container>
  );
}
