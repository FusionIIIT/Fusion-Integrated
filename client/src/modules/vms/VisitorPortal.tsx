import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Container, FileInput, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { errorMessage, http } from "../../lib/http";

type Host = { user_id: number; display_name: string; department: string };
type Visit = { id: number; status: string; purpose: string; starts_at: string; ends_at: string;
  decision_reason: string; approved_zones: string[] };

export function VisitorRegistrationPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [idType, setIdType] = useState<string | null>("passport");
  const [idValue, setIdValue] = useState("");
  const [identityDocument, setIdentityDocument] = useState<File | null>(null);
  const [purpose, setPurpose] = useState("");
  const [query, setQuery] = useState("");
  const [hostId, setHostId] = useState<string | null>(null);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [error, setError] = useState("");
  const [reference, setReference] = useState<number | null>(null);
  const hosts = useQuery({ queryKey: ["vms", "public-hosts", query], enabled: query.trim().length >= 2,
    queryFn: async () => (await http.get<Host[]>("/vms/public/hosts", { params: { q: query } })).data });
  const options = useMemo(() => (hosts.data ?? []).map((h) => ({
    value: String(h.user_id), label: `${h.display_name}${h.department ? ` · ${h.department}` : ""}`,
  })), [hosts.data]);

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    try {
      const form = new FormData();
      form.set("name", name); form.set("email", email); form.set("phone", phone);
      form.set("id_type", idType ?? ""); form.set("id_value", idValue);
      form.set("identity_document", identityDocument as File);
      form.set("purpose", purpose); form.set("host_user_id", String(Number(hostId)));
      form.set("starts_at", new Date(startsAt).toISOString());
      form.set("ends_at", new Date(endsAt).toISOString());
      const response = await http.post<{ id: number }>("/vms/registrations", form);
      setReference(response.data.id);
      setIdValue("");
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  if (reference !== null) return <Container size="sm" py="xl"><Stack>
    <Title order={2}>Request submitted</Title>
    <Alert title={`Reference ${reference}`} color="green">
      The host will review your request. We sent a secure status link to your email address.
    </Alert>
    <Button variant="light" onClick={() => setReference(null)}>Submit another request</Button>
  </Stack></Container>;

  return <Container size="sm" py="xl"><form onSubmit={submit}><Stack>
    <Title order={2}>Request a campus visit</Title>
    <Text c="dimmed">Enter your details and choose an institute host. Your identity number is used for a protected duplicate and security check.</Text>
    {error && <Alert color="red">{error}</Alert>}
    <TextInput label="Full name" value={name} onChange={(e) => setName(e.currentTarget.value)} required maxLength={160} />
    <TextInput label="Email" type="email" value={email} onChange={(e) => setEmail(e.currentTarget.value)} required maxLength={254} />
    <TextInput label="Phone" value={phone} onChange={(e) => setPhone(e.currentTarget.value)} maxLength={32} />
    <Select label="Identity document type" value={idType} onChange={setIdType} required data={[
      { value: "passport", label: "Passport" }, { value: "national_id", label: "National ID" },
      { value: "driving_license", label: "Driving licence" }, { value: "voter_id", label: "Voter ID" },
      { value: "other_government_id", label: "Other government ID" },
    ]} />
    <TextInput label="Identity number" value={idValue} onChange={(e) => setIdValue(e.currentTarget.value)} required maxLength={100} />
    <FileInput label="Identity document" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
      value={identityDocument} onChange={setIdentityDocument} required />
    <Text size="sm" c="dimmed">PDF, PNG, or JPEG up to 5 MB. The document is scanned before gate entry is permitted.</Text>
    <Textarea label="Purpose of visit" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} required maxLength={500} />
    <TextInput label="Search host by name or department" value={query} onChange={(e) => { setQuery(e.currentTarget.value); setHostId(null); }} minLength={2} />
    {hosts.isError && <Text c="red" size="sm">Host directory is temporarily unavailable.</Text>}
    <Select label="Host" value={hostId} onChange={setHostId} data={options} searchable nothingFoundMessage="No matching hosts" required />
    <TextInput label="Visit starts" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.currentTarget.value)} required />
    <TextInput label="Visit ends" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.currentTarget.value)} required />
    <Button type="submit" disabled={!idType || !hostId || !identityDocument}>Submit visit request</Button>
  </Stack></form></Container>;
}

export function VisitorAccessPage() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(() => params.get("token") ?? "");
  const [visits, setVisits] = useState<Visit[] | null>(null);
  const [error, setError] = useState("");
  const checkout = useMutation({ mutationFn: async (visitId: number) =>
    (await http.post(`/vms/visitor/requests/${visitId}/checkout`, {},
      { headers: { "X-Visitor-Token": token } })).data,
    onMutate: () => setError(""),
    onSuccess: (_data, visitId) => setVisits((prior) => prior?.map((visit) =>
      visit.id === visitId ? { ...visit, status: "completed" } : visit) ?? null),
    onError: () => setError("Self-checkout could not be confirmed. Ask Security Personnel to record your exit.") });
  useEffect(() => {
    if (params.has("token")) window.history.replaceState({}, "", "/vms/access");
  }, [params]);

  async function loadVisits(event: React.FormEvent) {
    event.preventDefault(); setError("");
    try {
      const response = await http.get<Visit[]>("/vms/visitor/requests", {
        headers: { "X-Visitor-Token": token },
      });
      setVisits(response.data);
    } catch {
      setError("This secure status link is invalid or has expired. Use the latest link from your email.");
      setVisits(null);
    }
  }

  return <Container size="lg" py="xl"><Stack>
    <Title order={2}>Your visitor requests</Title>
    <form onSubmit={loadVisits}><Stack>
      {!params.has("token") && <TextInput label="Secure access token" value={token}
        onChange={(e) => setToken(e.currentTarget.value)} required />}
      <Button type="submit">View requests</Button>
    </Stack></form>
    {error && <Alert color="red">{error}</Alert>}
    {visits && <Table withTableBorder striped><Table.Thead><Table.Tr>
      <Table.Th>Reference</Table.Th><Table.Th>Purpose</Table.Th><Table.Th>Visit time</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th>
    </Table.Tr></Table.Thead><Table.Tbody>{visits.map((v) => <Table.Tr key={v.id}>
      <Table.Td>{v.id}</Table.Td><Table.Td>{v.purpose}</Table.Td>
      <Table.Td>{new Date(v.starts_at).toLocaleString()} – {new Date(v.ends_at).toLocaleString()}</Table.Td>
      <Table.Td>{v.status.replaceAll("_", " ")}{v.decision_reason ? ` · ${v.decision_reason}` : ""}</Table.Td>
      <Table.Td>{v.status === "on_site" && <Button size="xs" variant="light"
        loading={checkout.isPending} onClick={() => checkout.mutate(v.id)}>Check out</Button>}</Table.Td>
    </Table.Tr>)}</Table.Tbody></Table>}
  </Stack></Container>;
}
