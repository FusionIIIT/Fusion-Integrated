import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert, Badge, Button, Card, Container, Group, Loader, Select, Stack,
  Table, Text, Textarea, TextInput, Title,
} from "@mantine/core";
import { errorMessage, http } from "../../lib/http";

type Page = "records" | "leave" | "appraisals" | "claims" | "approvals" | "admin" | "audit" | "notifications";
type Row = Record<string, unknown>;
const TITLES: Record<Page, string> = {
  records: "My service record", leave: "Leave requests", appraisals: "Yearly appraisals",
  claims: "LTC and CPDA claims", approvals: "Assigned approvals", admin: "HR administration",
  audit: "Audit trail", notifications: "Notifications",
};

function valueText(value: unknown): string {
  return value === null || value === undefined ? "—" :
    typeof value === "object" ? JSON.stringify(value) : String(value);
}

function Results({ rows, actions }: { rows: Row[]; actions?: (row: Row) => ReactNode }) {
  const first = rows[0];
  if (!first) return <Text c="dimmed" size="sm">No records yet.</Text>;
  return <Table.ScrollContainer minWidth={650}><Table striped highlightOnHover withTableBorder>
    <Table.Thead><Table.Tr>{Object.keys(first).map(k => <Table.Th key={k}>{k.replaceAll("_", " ")}</Table.Th>)}{actions && <Table.Th>Actions</Table.Th>}</Table.Tr></Table.Thead>
    <Table.Tbody>{rows.map((row, i) => <Table.Tr key={String(row.id ?? i)}>{Object.keys(first).map(k => <Table.Td key={k} maw={250} style={{ overflowWrap: "anywhere" }}>{k === "status" ? <Badge variant="light">{valueText(row[k])}</Badge> : <Text size="xs">{valueText(row[k])}</Text>}</Table.Td>)}{actions && <Table.Td>{actions(row)}</Table.Td>}</Table.Tr>)}</Table.Tbody>
  </Table></Table.ScrollContainer>;
}

export default function HrPage({ page }: { page: Page }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [kind, setKind] = useState("ltc");
  const [claimType, setClaimType] = useState("advance");
  const [leaveType, setLeaveType] = useState("casual");
  const [days, setDays] = useState("1");
  const [justification, setJustification] = useState("");
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [summary, setSummary] = useState("");
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");
  const [documents, setDocuments] = useState("");
  const [userId, setUserId] = useState("");
  const [category, setCategory] = useState("faculty");
  const [department, setDepartment] = useState("");
  const [designation, setDesignation] = useState("");
  const [leaveBalances, setLeaveBalances] = useState('{"casual":12,"restricted":2,"medical":15,"earned":30,"vacation":30,"sabbatical":180}');
  const [requestKind, setRequestKind] = useState("leave");
  const [authorities, setAuthorities] = useState("HOD,Director");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("recorded");
  const [paymentReference, setPaymentReference] = useState("");
  const [reviewerRoles, setReviewerRoles] = useState("HOD,Director");

  const query = useQuery({
    queryKey: ["hreis", page],
    queryFn: async (): Promise<Row> => {
      if (page === "admin") {
        const [records, routes, windows] = await Promise.all([
          http.get("/hreis/records"), http.get("/hreis/routes"), http.get("/hreis/windows"),
        ]);
        return { records: records.data.results, routes: routes.data.results, windows: windows.data.results };
      }
      const path: Record<Exclude<Page, "admin">, string> = {
        records: "records/me", leave: "leave", appraisals: "appraisals", claims: "claims",
        approvals: "approvals", audit: "audit", notifications: "notifications",
      };
      return (await http.get<Row>(`/hreis/${path[page]}`)).data;
    },
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: async ({ url, data }: {url: string; data: Row}) =>
      (await http.post(`/hreis/${url}`, data)).data,
    onSuccess: async () => {
      setError(""); setSuccess("Saved successfully.");
      await queryClient.invalidateQueries({ queryKey: ["hreis"] });
    },
    onError: (e: unknown) => { setSuccess(""); setError(errorMessage(e)); },
  });
  const submit = (url: string, data: Row) => { setError(""); setSuccess(""); mutation.mutate({ url, data }); };
  const roles = () => reviewerRoles.split(",").map(s => s.trim()).filter(Boolean);
  const routeRoles = () => authorities.split(",").map(s => s.trim()).filter(Boolean);
  const rows = (key = "results"): Row[] => {
    const v = query.data?.[key];
    return Array.isArray(v) ? v as Row[] : [];
  };

  return <Container size="xl" py="lg"><Stack gap="md">
    <Title order={2}>{TITLES[page]}</Title>
    {error && <Alert color="red" title="Request failed">{error}</Alert>}
    {success && <Alert color="green">{success}</Alert>}
    {query.isPending && <Loader size="sm" />}
    {query.isError && <Alert color="red">{errorMessage(query.error)}</Alert>}

    {page === "records" && query.data && <Card withBorder><Text size="sm" c="dimmed" mb="xs">Official HR information is read-only for employees.</Text><Results rows={[query.data]} /></Card>}

    {page === "leave" && <>
      <Card withBorder><Stack><Title order={4}>Apply for leave</Title>
        <Select label="Leave type" data={["casual", "restricted", "medical", "earned", "vacation", "sabbatical"]} value={leaveType} onChange={v => setLeaveType(v ?? "casual")} />
        <TextInput label="Duration (days)" type="number" value={days} onChange={e => setDays(e.currentTarget.value)} />
        <Textarea label="Justification" value={justification} onChange={e => setJustification(e.currentTarget.value)} />
        <Button loading={mutation.isPending} onClick={() => submit("leave", { leave_type: leaveType, days: Number(days), justification })}>Submit leave request</Button>
      </Stack></Card><Title order={4}>My leave history</Title><Results rows={rows()} />
    </>}

    {page === "appraisals" && <>
      <Card withBorder><Stack><Title order={4}>Submit yearly appraisal</Title>
        <TextInput label="Year" type="number" value={year} onChange={e => setYear(e.currentTarget.value)} />
        <Textarea label="Appraisal summary" value={summary} onChange={e => setSummary(e.currentTarget.value)} />
        <Text size="sm" c="dimmed">Submissions require an HR-configured open appraisal window.</Text>
        <Button loading={mutation.isPending} onClick={() => submit("appraisals", { year: Number(year), content: { summary } })}>Submit appraisal</Button>
      </Stack></Card><Title order={4}>My appraisals</Title><Results rows={rows()} />
    </>}

    {page === "claims" && <>
      <Card withBorder><Stack><Title order={4}>Submit LTC / CPDA claim</Title>
        <Group grow><Select label="Claim category" value={kind} onChange={v => setKind(v ?? "ltc")} data={[{ value: "ltc", label: "Leave Travel Concession" }, { value: "cpda", label: "Professional Development Allowance" }]} />
        <Select label="Claim type" value={claimType} onChange={v => setClaimType(v ?? "advance")} data={["advance", "reimbursement"]} /></Group>
        <Textarea label="Purpose" value={purpose} onChange={e => setPurpose(e.currentTarget.value)} />
        <TextInput label="Amount" type="number" value={amount} onChange={e => setAmount(e.currentTarget.value)} />
        <Textarea label="Supporting document references (one per line)" value={documents} onChange={e => setDocuments(e.currentTarget.value)} />
        <Text size="sm" c="dimmed">Enter references to existing approved documents; HR-EIS records references but does not upload documents.</Text>
        <Button loading={mutation.isPending} onClick={() => submit("claims", {kind, claim_type: claimType, purpose, amount: Number(amount), documents: documents.split("\n").map(x => x.trim()).filter(Boolean)})}>Submit claim</Button>
      </Stack></Card><Title order={4}>My claims</Title><Results rows={rows()} />
    </>}

    {page === "approvals" && <>
      <Text size="sm" c="dimmed">Only requests currently assigned to your active Fusion role appear. Switch roles in the shell when needed.</Text>
      <Card withBorder><Stack><Title order={4}>Leave approvals</Title><Results rows={rows("leave")} actions={r => <Group gap="xs" wrap="nowrap">{["approve", "reject", "forward"].map(outcome => <Button size="xs" variant="light" key={outcome} loading={mutation.isPending} onClick={() => submit(`leave/${r.id}/decision`, { outcome })}>{outcome}</Button>)}</Group>} /></Stack></Card>
      <Card withBorder><Stack><Title order={4}>Claim verification, approval and settlement</Title>
        <Group><TextInput label="External financial reference" value={paymentReference} onChange={e => setPaymentReference(e.currentTarget.value)} /><TextInput label="Payment status" value={paymentStatus} onChange={e => setPaymentStatus(e.currentTarget.value)} /></Group>
        <Results rows={rows("claims")} actions={r => <Group gap="xs">
          {r.status === "awaiting_hr" && <Button size="xs" onClick={() => submit(`claims/${r.id}/verify`, { documents_verified: true, eligible: true })}>Confirm HR verification</Button>}
          {r.status === "pending" && ["approve", "reject", "forward"].map(outcome => <Button key={outcome} size="xs" variant="light" onClick={() => submit(`claims/${r.id}/decision`, { outcome })}>{outcome}</Button>)}
          {r.status === "approved" && <Button size="xs" onClick={() => submit(`claims/${r.id}/process`, {payment_reference: paymentReference, payment_status: paymentStatus})}>Record settlement status</Button>}
        </Group>} />
      </Stack></Card>
      <Card withBorder><Stack><Title order={4}>Appraisal reviews</Title>
        <TextInput label="Ordered reviewer roles, comma-separated (for HR assignment)" value={reviewerRoles} onChange={e => setReviewerRoles(e.currentTarget.value)} />
        <Results rows={rows("appraisals")} actions={r => <Group gap="xs">{r.status === "submitted" ?
          <Button size="xs" onClick={() => submit(`appraisals/${r.id}/assign`, { reviewer_roles: roles() })}>Assign reviewers</Button> :
          <Button size="xs" onClick={() => submit(`appraisals/${r.id}/review`, {})}>Review / finalize</Button>}</Group>} />
      </Stack></Card>
    </>}

    {page === "admin" && <>
      <Card withBorder><Stack><Title order={4}>Create official service record</Title>
        <Group grow><TextInput label="IAM user ID" type="number" value={userId} onChange={e => setUserId(e.currentTarget.value)} /><Select label="Employee category" data={["faculty", "staff"]} value={category} onChange={v => setCategory(v ?? "faculty")} /></Group>
        <Group grow><TextInput label="Department" value={department} onChange={e => setDepartment(e.currentTarget.value)} /><TextInput label="Designation" value={designation} onChange={e => setDesignation(e.currentTarget.value)} /></Group>
        <Textarea label="Leave balances (JSON by leave type)" value={leaveBalances} onChange={e => setLeaveBalances(e.currentTarget.value)} />
        <Button loading={mutation.isPending} onClick={() => { try { submit("records", {user_id: Number(userId), category, department, designation, leave_balances: JSON.parse(leaveBalances)}); } catch { setError("Invalid leave-balances JSON."); } }}>Create service record</Button>
        <Results rows={rows("records")} />
      </Stack></Card>
      <Card withBorder><Stack><Title order={4}>Configure request approval hierarchy</Title>
        <Group grow><Select label="Employee category" data={["faculty", "staff"]} value={category} onChange={v => setCategory(v ?? "faculty")} /><Select label="Request type" data={["leave", "ltc", "cpda"]} value={requestKind} onChange={v => setRequestKind(v ?? "leave")} /></Group>
        <TextInput label="Ordered approving authority roles, comma-separated" value={authorities} onChange={e => setAuthorities(e.currentTarget.value)} />
        <Button onClick={() => submit("routes", {category, request_kind: requestKind, authorities: routeRoles()})}>Save workflow</Button><Results rows={rows("routes")} />
      </Stack></Card>
      <Card withBorder><Stack><Title order={4}>Appraisal submission window</Title>
        <TextInput label="Year" value={year} onChange={e => setYear(e.currentTarget.value)} />
        <Group grow><TextInput label="Start date/time (ISO 8601)" value={opensAt} onChange={e => setOpensAt(e.currentTarget.value)} placeholder="2026-10-01T00:00:00+05:30" /><TextInput label="End date/time (ISO 8601)" value={closesAt} onChange={e => setClosesAt(e.currentTarget.value)} placeholder="2026-10-31T23:59:00+05:30" /></Group>
        <Button onClick={() => submit("windows", {year: Number(year), opens_at: opensAt, closes_at: closesAt})}>Save window</Button><Results rows={rows("windows")} />
      </Stack></Card>
    </>}

    {page === "audit" && <Card withBorder><Text size="sm" mb="sm" c="dimmed">Audit entries are append-only through the HR-EIS API.</Text><Results rows={rows()} /></Card>}
    {page === "notifications" && <Card withBorder><Results rows={rows()} actions={r => !r.read_at && <Button size="xs" variant="light" onClick={() => submit(`notifications/${r.id}/read`, {})}>Mark read</Button>} /></Card>}
  </Stack></Container>;
}
