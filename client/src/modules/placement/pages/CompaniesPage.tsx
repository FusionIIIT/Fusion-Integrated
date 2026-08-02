import { useState } from "react";
import {
  Badge, Button, Card, Code, Container, Group, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBuilding, FaPlus, FaUserPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCompanies, useCompanyDecision, useInviteRecruiter, useRegisterCompany,
} from "../api/hooks";
import type { Company } from "../api/types";

const APPROVAL_COLOR: Record<string, string> = {
  pending: "yellow", approved: "green", rejected: "red",
};

export default function CompaniesPage() {
  const { data, isPending, error } = useCompanies();
  const decide = useCompanyDecision();
  const [registering, setRegistering] = useState(false);
  const [rejecting, setRejecting] = useState<Company | null>(null);
  const [inviting, setInviting] = useState<Company | null>(null);
  const [note, setNote] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function approve(c: Company) {
    decide.mutate({ id: c.id, action: "approve", note: "" }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Approved",
        message: `${c.name} can now be invited and post roles.`,
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not approve", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Companies"
        subtitle="Registration, approval and recruiter access"
        action={
          <Button leftSection={<FaPlus size={12} />}
            onClick={() => setRegistering(true)}>
            Register company
          </Button>
        }
      />

      <Card padding="lg">
        <DataTable<Company>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={980}
          columns={[
            {
              key: "name", header: "Company",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.name}</Text>
                  <Text size="xs" c="dimmed">
                    {[r.sector, r.hq_city].filter(Boolean).join(" · ") || "—"}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "approval_status", header: "Approval",
              render: (r) => (
                <Badge color={APPROVAL_COLOR[r.approval_status] ?? "gray"}
                  variant="light">
                  {r.approval_status}
                </Badge>
              ),
            },
            {
              key: "status", header: "Relationship",
              render: (r) => (
                <Badge
                  color={r.status === "blacklisted" ? "red"
                    : r.status === "active" ? "teal" : "gray"}
                  variant="light"
                >
                  {r.status}
                </Badge>
              ),
            },
            {
              key: "contact", header: "Primary contact",
              render: (r) => {
                const c = r.contacts?.find((x) => x.is_primary) ?? r.contacts?.[0];
                return c ? (
                  <Stack gap={0}>
                    <Text size="sm">{c.name || "—"}</Text>
                    <Text size="xs" c="dimmed">{c.email}</Text>
                  </Stack>
                ) : "—";
              },
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  {r.approval_status === "pending" && (
                    <>
                      <Button size="xs" onClick={() => approve(r)}
                        loading={decide.isPending}>
                        Approve
                      </Button>
                      <Button size="xs" variant="subtle" color="red"
                        onClick={() => { setRejecting(r); setNote(""); }}>
                        Reject
                      </Button>
                    </>
                  )}
                  {r.can_operate && (
                    <Button
                      size="xs" variant="light"
                      leftSection={<FaUserPlus size={10} />}
                      onClick={() => setInviting(r)}
                    >
                      Invite recruiter
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaBuilding,
            title: "No companies yet",
            description: "Register a company to start the approval process.",
          }}
        />
      </Card>

      <RegisterModal opened={registering} onClose={() => setRegistering(false)} />

      <FormModal
        opened={rejecting != null} onClose={() => setRejecting(null)}
        title={`Reject ${rejecting?.name ?? ""}`}
        subtitle="The company cannot post roles or hold recruiter accounts"
        onSubmit={() => rejecting && decide.mutate(
          { id: rejecting.id, action: "reject", note },
          {
            onSuccess: () => { setRejecting(null); },
            onError: (e) => notifications.show({
              color: "red", title: "Could not reject", message: errorMessage(e),
            }),
          },
        )}
        submitLabel="Reject" danger submitting={decide.isPending}
        disabled={!note.trim()}
      >
        <Textarea
          label="Reason" required autosize minRows={3} value={note}
          onChange={(e) => setNote(e.currentTarget.value)} maxLength={300}
        />
      </FormModal>

      <InviteModal company={inviting} onClose={() => setInviting(null)} />
    </Container>
  );
}

function RegisterModal({ opened, onClose }: {
  opened: boolean; onClose: () => void;
}) {
  const register = useRegisterCompany();
  const [f, setF] = useState({
    name: "", sector: "", website: "", hq_city: "",
    contact_name: "", contact_email: "", contact_phone: "",
  });

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Register a company"
      subtitle="Recorded as pending — it grants nothing until approved"
      onSubmit={() => register.mutate(f, {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Registered",
            message: "Awaiting approval.",
          });
          onClose();
        },
      })}
      submitLabel="Register" submitting={register.isPending}
      error={register.error} disabled={!f.name.trim()}
    >
      <Stack gap="md">
        <TextInput label="Company name" required value={f.name}
          onChange={(e) => setF({ ...f, name: e.currentTarget.value })} />
        <Group grow>
          <TextInput label="Sector" value={f.sector}
            onChange={(e) => setF({ ...f, sector: e.currentTarget.value })} />
          <TextInput label="HQ city" value={f.hq_city}
            onChange={(e) => setF({ ...f, hq_city: e.currentTarget.value })} />
        </Group>
        <TextInput label="Website" value={f.website} placeholder="https://…"
          onChange={(e) => setF({ ...f, website: e.currentTarget.value })} />
        <Text size="sm" fw={600} mt="xs">Primary contact</Text>
        <Group grow>
          <TextInput label="Name" value={f.contact_name}
            onChange={(e) => setF({ ...f, contact_name: e.currentTarget.value })} />
          <TextInput label="Email" value={f.contact_email}
            onChange={(e) => setF({ ...f, contact_email: e.currentTarget.value })} />
        </Group>
      </Stack>
    </FormModal>
  );
}

function InviteModal({ company, onClose }: {
  company: Company | null; onClose: () => void;
}) {
  const invite = useInviteRecruiter();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [token, setToken] = useState<string | null>(null);

  function close() { setToken(null); setEmail(""); setName(""); onClose(); }

  return (
    <FormModal
      opened={company != null} onClose={close}
      title={`Invite a recruiter at ${company?.name ?? ""}`}
      subtitle="Creates a portal account scoped to this company only"
      onSubmit={() => company && invite.mutate(
        { company_id: company.id, email, full_name: name },
        { onSuccess: (d) => setToken(d.invite_token) },
      )}
      submitLabel={token ? "Done" : "Send invitation"}
      submitting={invite.isPending} error={invite.error}
      disabled={!token && !email.trim()}
    >
      {token ? (
        <Stack gap="sm">
          <Text size="sm">
            The invitation link is shown <b>once</b>. Only its digest is stored,
            so it cannot be retrieved again — pass it to the recruiter now.
          </Text>
          <Code block>{`${window.location.origin}/recruiter/accept?token=${token}`}</Code>
          <Text size="xs" c="dimmed">Expires in 72 hours.</Text>
        </Stack>
      ) : (
        <Stack gap="md">
          <TextInput
            label="Recruiter email" required value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
          />
          <TextInput
            label="Full name" value={name}
            onChange={(e) => setName(e.currentTarget.value)}
          />
          <Text size="xs" c="dimmed">
            A recruiter can only ever see their own company&apos;s postings and
            applicants. They cannot reach the institute directory.
          </Text>
        </Stack>
      )}
    </FormModal>
  );
}
