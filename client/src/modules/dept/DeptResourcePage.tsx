import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Card, Container, Group, Loader, Select, Stack, Text, TextInput, Textarea, Title } from "@mantine/core";
import { useState } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { http } from "../../lib/http";

interface Props { resource: string }
type Row = Record<string, unknown>;
const titles: Record<string, string> = { announcements: "Department Announcements", stock: "Inventory and Stock Requests", feedback: "Confidential Feedback", timetable: "Class and Lab Timetable", resources: "Lab Resources", profiles: "Department Profiles", details: "Department Details" };

export default function DeptResourcePage({ resource }: Props) {
  const { session, can } = useAuth();
  const queryClient = useQueryClient();
  const profileDepartment = session?.user.department?.trim() ?? "";
  const fallbackDepartmentCode = /^[A-Z0-9_-]{2,48}$/i.test(profileDepartment)
    ? profileDepartment.toUpperCase()
    : "";
  const contexts = session?.department_contexts?.length
    ? session.department_contexts
    : fallbackDepartmentCode
      ? [{ code: fallbackDepartmentCode, name: fallbackDepartmentCode }]
      : [];
  const [department, setDepartment] = useState(contexts[0]?.code ?? "");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [itemId, setItemId] = useState("");
  const [purpose, setPurpose] = useState("");
  const [name, setName] = useState("");
  const [cohort, setCohort] = useState("");
  const [room, setRoom] = useState("");
  const [weekday, setWeekday] = useState("1");
  const [startsAt, setStartsAt] = useState("09:00");
  const [endsAt, setEndsAt] = useState("10:00");
  const [userId, setUserId] = useState("");
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("General");
  const [resolution, setResolution] = useState("");

  const endpoint = resource === "stock" ? "stock-requests" : resource;
  const list = useQuery({
    queryKey: ["dept", endpoint, department],
    queryFn: async () => (await http.get<Row[]>(`/dept/${endpoint}/`, { params: { department_code: department } })).data,
    enabled: !!department,
  });
  const inventory = useQuery({
    queryKey: ["dept", "inventory", department],
    queryFn: async () => (await http.get<Row[]>("/dept/inventory/", { params: { department_code: department } })).data,
    enabled: resource === "stock" && !!department,
  });
  const academic = useQuery({
    queryKey: ["dept", "academic-info", department],
    queryFn: async () => (await http.get<Row>("/dept/academic-info/", { params: { department_code: department } })).data,
    enabled: resource === "timetable" && !!department,
  });
  const notifications = useQuery({
    queryKey: ["dept", "notifications"],
    queryFn: async () => (await http.get<Row[]>("/dept/notifications/")).data,
  });
  const write = useMutation({
    mutationFn: async (payload: Row) => (await http.post(`/dept/${endpoint}/`, { ...payload, department_code: department })).data,
    onSuccess: () => { setTitle(""); setBody(""); setPurpose(""); queryClient.invalidateQueries({ queryKey: ["dept"] }); },
  });
  const addItem = useMutation({
    mutationFn: async (payload: Row) => (await http.post("/dept/inventory/", { ...payload, department_code: department })).data,
    onSuccess: () => { setName(""); queryClient.invalidateQueries({ queryKey: ["dept"] }); },
  });
  const act = useMutation({
    mutationFn: async ({ id, action, payload = {} }: { id: number; action: string; payload?: Row }) => (await http.post(`/dept/${endpoint}/${id}/${action}/`, { ...payload, department_code: department })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dept"] }),
  });
  const canCreate = resource === "announcements" ? can("dept.announcement.create")
    : resource === "stock" ? can("dept.stock_request.create")
    : resource === "feedback" ? can("dept.feedback.create")
        : resource === "timetable" ? can("dept.timetable.create")
          : resource === "resources" ? can("dept.resource.create")
            : resource === "profiles" ? can("dept.profile.update")
              : can("dept.department.update");

  if (!contexts.length) return <Container size="md" py="xl"><Alert color="yellow" title="Department context unavailable">Your IAM profile does not currently include a DEPT department context. Ask the IAM administrator to configure the department assignment.</Alert></Container>;
  return <Container size="lg" py="xl">
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div><Title order={2}>{titles[resource] ?? "Department"}</Title><Text c="dimmed" mt={4}>Department records are scoped to your current Fusion role.</Text></div>
        {contexts.length > 1 && <Select label="Department" data={contexts.map((c) => ({ value: c.code, label: c.name ?? c.code }))} value={department} onChange={(v) => setDepartment(v ?? "")} />}
      </Group>
      {notifications.data?.length ? <Card withBorder><Text fw={600}>Notifications</Text><Stack gap="xs" mt="sm">{notifications.data.slice(0, 3).map((n) => <Text key={String(n.id)} size="sm">{String(n.subject)} — {String(n.body)}</Text>)}</Stack></Card> : null}
      {resource === "timetable" && academic.data && <Card withBorder><Text fw={600}>Academic program</Text><Text size="sm">{String(academic.data.programme || "Program not listed")} · {String(academic.data.discipline || "Discipline not listed")} · Batch {String(academic.data.batch_year || "not listed")}</Text></Card>}
      {resource === "stock" && <Card withBorder><Stack><Title order={4}>Current Inventory</Title>{inventory.isPending ? <Loader size="sm" /> : (inventory.data ?? []).map((item) => <Group key={String(item.id)} justify="space-between"><Text>{String(item.name)} <Text span c="dimmed" size="xs">ID {String(item.id)}</Text></Text><Badge>{String(item.on_hand)} on hand · {String(item.reserved)} reserved</Badge></Group>)}{can("dept.stock_item.create") && <Group align="end"><TextInput label="New item" value={name} onChange={(e) => setName(e.currentTarget.value)} /><TextInput label="Quantity" type="number" value={quantity} onChange={(e) => setQuantity(e.currentTarget.value)} /><Button onClick={() => addItem.mutate({ name, quantity: Number(quantity) })} loading={addItem.isPending}>Add stock</Button></Group>}</Stack></Card>}
      {canCreate && <Card withBorder><Stack>
        <Title order={4}>{resource === "stock" ? "Request stock" : resource === "feedback" ? "Submit confidential feedback" : resource === "announcements" ? "Publish announcement" : `Add ${titles[resource]?.toLowerCase()}`}</Title>
        {(resource === "announcements" || resource === "feedback" || resource === "details" || resource === "timetable") && <TextInput label={resource === "timetable" ? "Class / lab title" : resource === "details" ? "Official department name (optional)" : "Title"} value={title} onChange={(e) => setTitle(e.currentTarget.value)} />}
        {(resource === "announcements" || resource === "feedback" || resource === "details") && <Textarea label={resource === "feedback" ? "Feedback" : "Message"} minRows={3} value={body} onChange={(e) => setBody(e.currentTarget.value)} />}
        {resource === "announcements" && <><TextInput label="Program (optional)" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} /><TextInput label="Academic year (optional)" value={quantity === "1" ? "" : quantity} onChange={(e) => setQuantity(e.currentTarget.value)} /></>}
        {resource === "stock" && <><Select label="Inventory item" data={(inventory.data ?? []).map((x) => ({ value: String(x.id), label: `${String(x.name)} (${String(Number(x.on_hand) - Number(x.reserved))} available)` }))} value={itemId} onChange={(v) => setItemId(v ?? "")} /><TextInput label="Quantity" type="number" value={quantity} onChange={(e) => setQuantity(e.currentTarget.value)} /><Textarea label="Purpose" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} /></>}
        {resource === "resources" && <><TextInput label="Resource name" value={name} onChange={(e) => setName(e.currentTarget.value)} /><TextInput label="Location" value={location} onChange={(e) => setLocation(e.currentTarget.value)} /></>}
        {resource === "timetable" && <><TextInput label="Cohort" value={cohort} onChange={(e) => setCohort(e.currentTarget.value)} /><TextInput label="Room / lab resource" value={room} onChange={(e) => setRoom(e.currentTarget.value)} /><Select label="Weekday" data={["1", "2", "3", "4", "5", "6", "7"].map((v) => ({ value: v, label: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][Number(v) - 1] ?? v }))} value={weekday} onChange={(v) => setWeekday(v ?? "1")} /><Group grow><TextInput label="Starts" type="time" value={startsAt} onChange={(e) => setStartsAt(e.currentTarget.value)} /><TextInput label="Ends" type="time" value={endsAt} onChange={(e) => setEndsAt(e.currentTarget.value)} /></Group></>}
        {resource === "profiles" && can("dept.profile.update") && <TextInput label="IAM user ID" type="number" value={userId} onChange={(e) => setUserId(e.currentTarget.value)} />}
        <Button loading={write.isPending} onClick={() => write.mutate(resource === "stock" ? { item_id: Number(itemId), quantity: Number(quantity), purpose } : resource === "resources" ? { name, location } : resource === "timetable" ? { title, cohort, resource: room, weekday: Number(weekday), starts_at: startsAt, ends_at: endsAt } : resource === "profiles" ? { user_id: Number(userId), details: {} } : resource === "details" ? { description: body } : resource === "announcements" ? { title, body, target_roles: ["student", "faculty"], programme: purpose, academic_year: quantity === "1" ? "" : quantity } : { title, body })}>Submit</Button>
        {write.error && <Alert color="red">{write.error.message}</Alert>}
      </Stack></Card>}
      {list.isPending && <Loader />}{list.error && <Alert color="red">Could not load this department data. {list.error.message}</Alert>}
      {(list.data ?? []).map((item) => <Card withBorder key={String(item.id ?? item.user_id ?? `${item.weekday}-${item.starts_at}`)}>
        <Group justify="space-between" align="start"><div><Text fw={600}>{String(item.title ?? item.name ?? item.display_name ?? item.status ?? "Department record")}</Text><Text size="sm" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>{String(item.body ?? item.description ?? item.resolution ?? "")}</Text></div><Badge variant="light">{String(item.status ?? item.kind ?? "Active")}</Badge></Group>
        {resource === "stock" && item.status === "pending" && can("dept.stock_request.approve") && <Group mt="md"><Button onClick={() => act.mutate({ id: Number(item.id), action: "approve" })}>Approve</Button><Button color="red" variant="light" onClick={() => act.mutate({ id: Number(item.id), action: "reject" })}>Reject</Button></Group>}
        {resource === "stock" && item.status === "approved" && can("dept.stock_request.update") && <Button mt="md" onClick={() => act.mutate({ id: Number(item.id), action: "issue" })}>Issue stock</Button>}
        {resource === "feedback" && item.status === "new" && can("dept.feedback.review") && <Group mt="md" align="end"><TextInput label="Category" value={category} onChange={(e) => setCategory(e.currentTarget.value)} /><Button onClick={() => act.mutate({ id: Number(item.id), action: "review", payload: { category } })}>Start review</Button></Group>}
        {resource === "feedback" && item.status === "under_review" && can("dept.feedback.review") && <Group mt="md" align="end"><TextInput label="Resolution / closure note" value={resolution} onChange={(e) => setResolution(e.currentTarget.value)} /><Button onClick={() => act.mutate({ id: Number(item.id), action: "resolve", payload: { resolution } })}>Resolve</Button><Button variant="light" onClick={() => act.mutate({ id: Number(item.id), action: "close", payload: { resolution } })}>Close</Button></Group>}
      </Card>)}
    </Stack>
  </Container>;
}
