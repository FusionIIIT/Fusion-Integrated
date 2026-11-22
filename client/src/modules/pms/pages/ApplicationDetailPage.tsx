import { useEffect, useState, type FormEvent } from "react";
import { Alert, Button, Card, Container, FileInput, Group, Select, Stack, Text, TextInput, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate, useParams } from "react-router-dom";

import { http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuth } from "../../../auth/AuthProvider";

type App = { id: string; application_number: string; title: string; abstract: string;
  detailed_description: string; claims: string; technical_domain: string; status: string };
type Doc = { id: number; document_type: string; original_filename: string; version: number;
  malware_scan_status: string; sensitivity: string };
type Inventor = { id: number; full_name: string; ownership_percent: string; agreement_status: string };

export default function ApplicationDetailPage() {
  const { appId } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const canCreate = session?.permissions.includes("pms.application.create") ?? false;
  const canInvent = session?.permissions.includes("pms.inventor.manage") ?? false;
  const canUpload = session?.permissions.includes("pms.document.upload") ?? false;
  const [app, setApp] = useState<App>();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [inventors, setInventors] = useState<Inventor[]>([]);
  const [error, setError] = useState<unknown>();
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({ title: "", abstract: "", detailed_description: "", claims: "", technical_domain: "" });
  const [person, setPerson] = useState({ full_name: "", email: "", ownership_percent: "100" });
  const [file, setFile] = useState<File | null>(null);
  const [sensitivity, setSensitivity] = useState("internal");

  async function refresh(id: string) {
    const [appRes, docRes, inventorRes] = await Promise.all([
      http.get<App>(`/pms/applications/${id}`),
      http.get<Doc[]>(`/pms/applications/${id}/documents`),
      http.get<Inventor[]>(`/pms/applications/${id}/inventors`),
    ]);
    setApp(appRes.data); setDocs(docRes.data); setInventors(inventorRes.data);
  }
  useEffect(() => {
    if (!appId) return;
    let active = true;
    Promise.all([
      http.get<App>(`/pms/applications/${appId}`),
      http.get<Doc[]>(`/pms/applications/${appId}/documents`),
      http.get<Inventor[]>(`/pms/applications/${appId}/inventors`),
    ]).then(([a, d, i]) => { if (active) { setApp(a.data); setDocs(d.data); setInventors(i.data); } })
      .catch((e: unknown) => { if (active) setError(e); });
    return () => { active = false; };
  }, [appId]);

  async function createDraft(event: FormEvent) {
    event.preventDefault(); setSaving(true);
    try {
      const { data } = await http.post<App>("/pms/applications", draft);
      navigate(`/pms/applications/${data.id}`, { replace: true });
    } catch (e) { setError(e); } finally { setSaving(false); }
  }
  async function addInventor(event: FormEvent) {
    event.preventDefault(); if (!appId) return; setSaving(true);
    try {
      await http.post(`/pms/applications/${appId}/inventors`, person);
      setPerson({ full_name: "", email: "", ownership_percent: "0" });
      await refresh(appId);
    } catch (e) { setError(e); } finally { setSaving(false); }
  }
  async function uploadDocument() {
    if (!appId || !file) return; setSaving(true);
    try {
      const body = new FormData(); body.append("file", file); body.append("document_type", "supporting");
      body.append("sensitivity", sensitivity);
      await http.post(`/pms/applications/${appId}/documents`, body);
      setFile(null); await refresh(appId);
      notifications.show({ title: "Document uploaded", message: "The file remains unavailable for submission until malware scanning reports it clean." });
    } catch (e) { setError(e); } finally { setSaving(false); }
  }
  async function submit() {
    if (!appId) return; setSaving(true);
    try { const { data } = await http.post<App>(`/pms/applications/${appId}/submit`); setApp(data); }
    catch (e) { setError(e); } finally { setSaving(false); }
  }

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  if (!appId) return (
    <Container size="lg">
      <PageHeader title="New patent application" subtitle="Create a draft before adding inventors and supporting documents." />
      <Card withBorder><form onSubmit={createDraft}><Stack>
        <TextInput label="Title" required value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.currentTarget.value })} />
        <TextInput label="Technical domain" required value={draft.technical_domain} onChange={(e) => setDraft({ ...draft, technical_domain: e.currentTarget.value })} />
        <Textarea label="Abstract" required minRows={3} value={draft.abstract} onChange={(e) => setDraft({ ...draft, abstract: e.currentTarget.value })} />
        <Textarea label="Detailed description" required minRows={5} value={draft.detailed_description} onChange={(e) => setDraft({ ...draft, detailed_description: e.currentTarget.value })} />
        <Textarea label="Claims" required minRows={4} value={draft.claims} onChange={(e) => setDraft({ ...draft, claims: e.currentTarget.value })} />
        <Group justify="flex-end"><Button variant="default" onClick={() => navigate("/pms/applications")}>Cancel</Button>
          <Button type="submit" loading={saving} disabled={!canCreate}>Save draft</Button></Group>
      </Stack></form></Card>
    </Container>
  );

  if (!app) return <Container size="lg"><Text c="dimmed">Loading application…</Text></Container>;
  const editable = ["draft", "needs_revision"].includes(app.status);
  return (
    <Container size="lg">
      <PageHeader title={app.application_number || "Application draft"} subtitle={app.title} />
      <Stack>
        <Card withBorder><Group justify="space-between"><div><Text fw={600}>Status</Text><Text>{app.status.replaceAll("_", " ")}</Text></div>
          {app.status === "draft" && <Button onClick={submit} loading={saving}>Submit for review</Button>}</Group>
          <Text size="sm" c="dimmed" mt="sm">Submission requires complete inventor shares, supporting PDFs, and a clean malware scan.</Text></Card>
        <Card withBorder><Title order={4} mb="sm">Inventors and agreements</Title>
          {inventors.map((x) => <Text key={x.id}>{x.full_name} · {x.ownership_percent}% · {x.agreement_status}</Text>)}
          {editable && canInvent && <form onSubmit={addInventor}><Stack mt="md">
            <TextInput label="Inventor name" required value={person.full_name} onChange={(e) => setPerson({ ...person, full_name: e.currentTarget.value })} />
            <TextInput label="Email" type="email" value={person.email} onChange={(e) => setPerson({ ...person, email: e.currentTarget.value })} />
            <TextInput label="Ownership share (%)" type="number" min="0" max="100" step="0.01" required value={person.ownership_percent} onChange={(e) => setPerson({ ...person, ownership_percent: e.currentTarget.value })} />
            <Button type="submit" loading={saving} w="fit-content">Add inventor</Button>
          </Stack></form>}
        </Card>
        <Card withBorder><Title order={4} mb="sm">Supporting documents</Title>
          {docs.map((x) => <Text key={x.id}>{x.original_filename} · v{x.version} · scan: {x.malware_scan_status}</Text>)}
          {editable && canUpload && <Stack mt="md"><Select label="Sensitivity" data={["public", "internal", "confidential", "restricted"]} value={sensitivity} onChange={(value) => { if (value) setSensitivity(value); }} />
            <FileInput label="PDF file" accept="application/pdf,.pdf" value={file} onChange={setFile} />
            <Button onClick={uploadDocument} disabled={!file} loading={saving} w="fit-content">Upload version</Button></Stack>}
        </Card>
        {app.status === "needs_revision" && <Alert color="yellow" title="Revision required">Upload updated documents and add a response to the Director feedback before resubmission.</Alert>}
      </Stack>
    </Container>
  );
}
