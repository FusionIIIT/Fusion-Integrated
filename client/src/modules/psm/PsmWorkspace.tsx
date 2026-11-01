import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Drawer, Group, Loader, Modal, NumberInput, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { FiArchive, FiArrowRight, FiBell, FiBox, FiCheckCircle, FiClipboard, FiClock, FiDollarSign, FiFileText, FiGrid, FiPackage, FiRefreshCw, FiSearch, FiSettings, FiShield, FiShoppingCart, FiTruck, FiUsers } from "react-icons/fi";
import { http, errorMessage, setCsrfToken } from "../../lib/http";
import "./psm.css";

type Row = Record<string, unknown> & { id: string };
type Workspace = Record<string, unknown> & { viewer: Viewer; metrics: Record<string, number> };
type Viewer = { user_id: number; name: string; role: string; department: string };
type Field = { key: string; label: string; type?: "number" | "textarea" | "json" | "datetime-local"; options?: { value: string; label: string }[]; initial?: string; optional?: boolean };
type Operation = { title: string; resource: string; id?: string; action?: string; fields: Field[]; report?: boolean };
const str = (v: unknown) => v == null ? "" : String(v);
const human = (v: unknown) => str(v).replaceAll("_", " ");
const shortId = (v: unknown) => str(v).slice(0, 8).toUpperCase();
const money = (v: unknown) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(v) || 0);
const date = (v: unknown) => v ? new Date(str(v)).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : "—";
const color = (v: unknown) => /paid|completed|verified|confirmed|resolved|authorized|approved/.test(str(v)) ? "teal" : /held|rejected|discrepancy|cancelled/.test(str(v)) ? "red" : /await|pending|submitted|reserved/.test(str(v)) ? "orange" : "blue";
const field = (key: string, label: string, type?: Field["type"]): Field => ({ key, label, type });
const sections = [
  { key: "dashboard", label: "Overview", icon: FiGrid }, { key: "indents", label: "Purchase requests", icon: FiClipboard },
  { key: "stock", label: "Stock & inventory", icon: FiBox }, { key: "transfers", label: "Stock transfers", icon: FiTruck },
  { key: "vendors", label: "Vendor directory", icon: FiUsers }, { key: "tenders", label: "Tenders & bids", icon: FiFileText },
  { key: "orders", label: "Purchase orders", icon: FiShoppingCart }, { key: "receipts", label: "Goods receipts", icon: FiPackage },
  { key: "cases", label: "Returns & warranty", icon: FiArchive }, { key: "invoices", label: "Invoices & payments", icon: FiDollarSign },
  { key: "reports", label: "Reports & schedules", icon: FiFileText }, { key: "audit", label: "Audit trail", icon: FiShield },
  { key: "notifications", label: "Notifications", icon: FiBell }, { key: "policies", label: "Procurement policy", icon: FiSettings },
];
const columns: Record<string, [string, string][]> = {
  indents: [["item", "Item / service"], ["quantity", "Quantity"], ["estimated_cost", "Estimate"], ["department", "Department"], ["status", "Status"]],
  stock: [["item", "Item"], ["location", "Store / department"], ["quantity", "On hand"], ["reserved", "Reserved"]],
  transfers: [["source", "Source stock"], ["destination", "Destination"], ["quantity", "Quantity"], ["status", "Status"]],
  vendors: [["name", "Vendor"], ["gst", "GST reference"], ["version", "Version"], ["verified", "Verified"]],
  tenders: [["indent", "Purchase request"], ["criteria", "Evaluation criteria"], ["closes_at", "Closes"], ["status", "Status"]],
  bids: [["vendor", "Vendor"], ["amount", "Bid value"], ["proposal", "Proposal"]],
  orders: [["indent", "Purchase request"], ["vendor", "Vendor"], ["amount", "Order value"], ["planned_delivery", "Expected delivery"], ["status", "Status"]],
  receipts: [["indent", "Purchase request"], ["accepted", "Accepted"], ["rejected", "Rejected"], ["confirmed_at", "Confirmed"], ["posted", "Stock posted"]],
  cases: [["indent", "Purchase request"], ["kind", "Case type"], ["description", "Issue"], ["status", "Status"]],
  invoices: [["number", "Invoice"], ["po", "Purchase order"], ["amount", "Invoice value"], ["quantity", "Quantity"], ["status", "Status"]],
  payments: [["invoice", "Invoice"], ["amount", "Amount"], ["reference", "Payment reference"]],
  reports: [["report", "Report"], ["created_at", "Generated"], ["filters", "Filters"]],
  schedules: [["report", "Report"], ["interval_hours", "Every (hours)"], ["next_run", "Next run"], ["enabled", "Active"]],
  notifications: [["event", "Event"], ["message", "Message"], ["created_at", "Received"], ["read_at", "Read"]],
  audit: [["action", "Action"], ["entity", "Record type"], ["actor_id", "Actor"], ["created_at", "Time"]],
  policies: [["name", "Policy"], ["active", "Active"], ["created_at", "Created"]],
};
const dateKeys = new Set(["created_at", "updated_at", "planned_delivery", "actual_delivery", "closes_at", "confirmed_at", "next_run", "read_at"]);

export function PreviewWorkspace() {
  const qc = useQueryClient();
  const [role, setRole] = useState("ps_admin");
  const [key, setKey] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("key") || sessionStorage.getItem("psm-preview-key") || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => { if (window.location.hash) history.replaceState(null, "", window.location.pathname); }, []);
  async function login() {
    setBusy(true); setError("");
    try {
      const { data } = await http.post("/psm-preview/login", { key, role });
      sessionStorage.setItem("psm-preview-key", key);
      qc.setQueryData(["session"], data);
      setCsrfToken(data.csrf_token);
      await qc.invalidateQueries({ queryKey: ["psm"] });
      setReady(true);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <div className="psm-preview">
    <div className="psm-demo-strip"><span><b>FUSION / PSM PREVIEW</b> · Synthetic data · Illustrative policy</span>
      <Group gap="xs"><Select aria-label="Preview actor" value={role} onChange={v => setRole(v || "ps_admin")} data={["employee", "department_admin", "department_head", "ps_admin", "accounts", "final_authority", "committee", "vendor", "auditor"].map(value => ({ value, label: human(value) }))} size="xs" />
      <Button size="xs" onClick={login} loading={busy}>{ready ? "Switch actor" : "Open preview"}</Button></Group></div>
    {!ready ? <div className="psm-login"><FiPackage size={40} /><h1>Purchase & Stores</h1><p>Explore the complete procurement workspace with synthetic institute records.</p>
      <TextInput label="Preview access key" type="password" value={key} onChange={e => setKey(e.target.value)} />
      {error && <Alert color="red">{error}</Alert>}<Button onClick={login} loading={busy}>Open workspace <FiArrowRight /></Button></div> : <>
      {error && <Alert color="red">{error}</Alert>}<PsmWorkspace preview /></>}
  </div>;
}

export default function PsmWorkspace({ preview = false }: { preview?: boolean }) {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["psm", "workspace"], queryFn: async () => (await http.get("/psm/workspace")).data as Workspace, refetchInterval: 20000, retry: false });
  const [tab, setTab] = useState("dashboard");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<{ resource: string; row: Row } | null>(null);
  const [op, setOp] = useState<Operation | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const data = query.data;
  const viewer = data?.viewer as unknown as Viewer | undefined;
  const metrics = data?.metrics as unknown as Record<string, number> | undefined;
  const role = viewer?.role || "";
  useEffect(() => { setSelected(null); setOp(null); setTab("dashboard"); setSearch(""); setPage(0); }, [viewer?.user_id]);
  const rows = (name: string): Row[] => Array.isArray(data?.[name]) ? data[name] as Row[] : [];
  const can = (...roles: string[]) => roles.includes(role);
  const optionRows = (resource: string, filter?: (r: Row) => boolean) => rows(resource).filter(filter || (() => true)).map(r => ({ value: r.id, label: resource === "indents" || resource === "stock" || resource === "transfer_sources" ? str(r.item)+" · "+(r.location ? str(r.location)+" · " : "")+shortId(r.id) : str(r.name || r.number || r.report || shortId(r.id)) }));
  const choices = (key: string, label: string, resource: string, filter?: (r: Row) => boolean): Field => ({ key, label, options: optionRows(resource, filter) });
  const fixed = (key: string, label: string, opts: string[]): Field => ({ key, label, options: opts.map(value => ({ value, label: human(value) })) });
  const show = (operation: Operation) => {
    setValues(Object.fromEntries(operation.fields.map(f => [f.key, f.initial || ""])));
    setError(""); setOp(operation);
  };
  const changeTab = (key: string) => { setTab(key); setSearch(""); setPage(0); if (key === "audit") void http.get("/psm/audit").then(() => query.refetch()); };
  async function submit() {
    if (!op) return;
    setSaving(true); setError("");
    try {
      const input: Record<string, unknown> = {};
      for (const f of op.fields) {
        if (f.optional && !values[f.key]) continue;
        input[f.key] = f.type === "json" ? JSON.parse(values[f.key] || "{}") : values[f.key];
      }
      if (op.report) {
        const response = await http.post("/psm/report", { data: input }, input.format === "csv" ? { responseType: "blob" } : {});
        if (input.format === "csv") {
          const url = URL.createObjectURL(response.data); const a = document.createElement("a");
          a.href = url; a.download = "psm-report.csv"; a.click(); URL.revokeObjectURL(url);
        }
        changeTab("reports");
      } else {
        const path = op.id ? "/psm/"+op.resource+"/"+op.id+"/actions" : "/psm/"+op.resource;
        await http.post(path, op.id ? { action: op.action, data: input } : { data: input });
      }
      setOp(null); setSelected(null); await qc.invalidateQueries({ queryKey: ["psm"] });
    } catch (e) { setError(e instanceof SyntaxError ? "Check the JSON field format." : errorMessage(e)); }
    finally { setSaving(false); }
  }
  const action = (resource: string, row: Row, name: string, title: string, fields: Field[] = []) => ({ resource, id: row.id, action: name, title, fields });
  const indentFields = [field("item", "Item or service"), field("quantity", "Quantity", "number"), field("estimated_cost", "Estimated total cost (INR)", "number"), field("justification", "Justification", "textarea")];
  const reportFields = [fixed("report", "Report type", can("accounts", "auditor") ? ["operational", "procurement", "stock", "financial", "audit"] : ["operational", "procurement", "stock"]), { ...field("filters", "Filters (JSON)", "json"), initial: "{}" }];
  function operations(resource: string, r: Row): Operation[] {
    const result: Operation[] = [];
    const status = str(r.status);
    if (resource === "indents") {
      const owner = r.requestor_id === viewer?.user_id;
      if (owner) {
        if (status === "draft") result.push(action(resource, r, "submit", "Submit request"));
        result.push(action(resource, r, "repeat", "Repeat as new draft"));
        const policy = r.policy_snapshot as Record<string, string[]> || {};
        for (const [cmd, label] of [["modify", "Modify request"], ["withdraw", "Withdraw request"], ["cancel", "Cancel request"]] as const) {
          if (policy[cmd+"_states"]?.includes(status)) result.push(action(resource, r, cmd, label, cmd === "modify" ? indentFields.map(f => ({ ...f, initial: str(r[f.key]) })) : []));
        }
        rows("receipts").filter(receipt => receipt.indent === r.id && !receipt.confirmed_at && Number(receipt.accepted) > 0).forEach(receipt => result.push(action(resource, r, "confirm_receipt", "Confirm receipt "+shortId(receipt.id), [{ key: "receipt_id", label: "Goods receipt", options: [{ value: receipt.id, label: shortId(receipt.id) }], initial: receipt.id }])));
      }
      if (can("department_admin", "ps_admin") && ["submitted", "modified"].includes(status)) result.push(action(resource, r, "reserve", "Check & reserve stock"));
      const route = r.approval_route as string[] || [];
      if (route[Number(r.approval_step)] === role && ["stock_reserved", "external_required", "awaiting_approval"].includes(status)) result.push(action(resource, r, "review", role === "department_head" ? "Review & recommend" : "Review request", [
        fixed("decision", "Decision", role === "department_head" ? ["approve", "changes", "reject"] : ["approve", "reject"]),
        { ...field("reason", "Decision reason / budget review", "textarea"), optional: true },
        ...(role === "department_admin" ? [field("priority", "Criticality / priority", "number"), { ...field("duplicate_review", "Duplicate review (required if flagged)", "textarea"), optional: true }] : []),
      ]));
      if (can("department_admin", "ps_admin") && status === "internal_approved") result.push(action(resource, r, "dispatch", "Schedule picking & dispatch", [field("pick_at", "Pick at", "datetime-local"), field("dispatch_at", "Dispatch at", "datetime-local")]));
    }
    if (resource === "vendors" && can("ps_admin")) {
      result.push(action(resource, r, "verify", "Verify vendor"));
      result.push(action(resource, r, "update", "Edit vendor master", [field("name", "Vendor name"), field("gst", "GST reference"), field("bank_details", "Bank details", "textarea"), field("compliance", "Compliance document references (JSON list)", "json")].map(f => ({ ...f, initial: typeof r[f.key] === "object" ? JSON.stringify(r[f.key]) : str(r[f.key]) }))));
    }
    if (resource === "tenders" && can("committee") && status !== "selected") {
      const bids = rows("bids").filter(b => b.tender === r.id).map(b => ({ value: b.id, label: shortId(b.id)+" · "+money(b.amount) }));
      result.push(action(resource, r, "evaluate", "Evaluate bid", [{ key: "bid", label: "Bid", options: bids }, { ...field("evaluation", "Evaluation for each criterion (JSON)", "json"), initial: JSON.stringify(Object.fromEntries((r.criteria as string[] || []).map(c => [c, ""]))) }]));
      result.push(action(resource, r, "select", "Approve tender selection", [{ key: "bid", label: "Evaluated bid", options: bids }, field("reason", "Committee decision", "textarea")]));
    }
    if (resource === "orders" && can("ps_admin")) {
      result.push(action(resource, r, "schedule", "Update delivery schedule", [field("planned_delivery", "Expected delivery", "datetime-local")]));
      if (status === "issued") result.push(action(resource, r, "deliver", "Record delivery", [field("actual_delivery", "Actual delivery", "datetime-local")]));
    }
    if (resource === "cases") {
      if (can("ps_admin", "vendor", "accounts")) result.push(action(resource, r, "communicate", "Record vendor communication", [field("message", "Message", "textarea")]));
      if (status === "open" && can("ps_admin")) {
        result.push(action(resource, r, "replace", "Request replacement", [field("resolution", "Replacement decision", "textarea")]));
        result.push(action(resource, r, "resolve", "Resolve return / warranty", [field("resolution", "Resolution and authorization", "textarea"), field("inventory_delta", "Inventory adjustment", "number"), field("accounting_delta", "Accounting adjustment (INR)", "number")]));
      }
    }
    if (resource === "invoices" && can("accounts")) {
      if (!["paid", "partially_paid"].includes(status)) result.push(action(resource, r, "verify", "Run three-way match"));
      if (status !== "paid") result.push(action(resource, r, "hold", "Place payment on hold", [field("reason", "Hold reason", "textarea")]));
      if (["verified", "partially_paid"].includes(status)) result.push(action(resource, r, "pay", "Record vendor payment", [field("amount", "Payment amount (INR)", "number"), field("reference", "External payment reference")]));
    }
    if (resource === "transfers" && can("department_admin", "ps_admin")) {
      const stock = rows("stock").find(s => s.id === r.source);
      if (status === "requested" && (role === "ps_admin" || stock?.location === viewer?.department)) result.push(action(resource, r, "dispatch", "Reserve & dispatch transfer"));
      if (status === "dispatched" && (role === "ps_admin" || r.destination === viewer?.department)) result.push(action(resource, r, "confirm", "Confirm transfer receipt"));
    }
    if (resource === "notifications" && !r.read_at) result.push(action(resource, r, "read", "Mark as read"));
    if (resource === "schedules" && r.enabled) result.push(action(resource, r, "disable", "Disable schedule"));
    return result;
  }
  function createOperation(resource: string): Operation | null {
    const base = { resource, title: "New record", fields: [] as Field[] };
    if (resource === "indents" && can("employee", "department_admin", "department_head", "ps_admin")) return { ...base, title: "New purchase request", fields: indentFields };
    if (resource === "stock" && can("department_admin", "ps_admin")) return { ...base, title: "Authorized stock correction", fields: [field("item", "Item"), ...(role === "ps_admin" ? [field("location", "Store / department")] : []), field("delta", "Quantity adjustment", "number"), field("source", "Source event / authorization reference"), field("reason", "Correction reason", "textarea")] };
    if (resource === "transfers" && can("department_admin", "ps_admin")) return { ...base, title: "Request stock transfer", fields: [choices("source", "Source stock", "transfer_sources"), ...(role === "ps_admin" ? [field("destination", "Destination department")] : []), field("quantity", "Quantity", "number"), field("reason", "Transfer reason", "textarea")] };
    if (resource === "vendors" && can("ps_admin")) return { ...base, title: "Onboard vendor", fields: [field("name", "Vendor name"), field("gst", "GST reference"), field("bank_details", "Bank details", "textarea"), { ...field("compliance", "Compliance document references (JSON list)", "json"), initial: '["document reference"]' }] };
    if (resource === "tenders" && can("ps_admin")) return { ...base, title: "Publish tender", fields: [choices("indent", "Authorized tender request", "indents", r => r.status === "authorized" && r.method === "tender"), { ...field("criteria", "Published evaluation criteria (JSON list)", "json"), initial: '["Technical suitability","Delivery","Price"]' }, field("closes_at", "Bid deadline", "datetime-local")] };
    if (resource === "bids" && can("vendor", "ps_admin")) return { ...base, title: "Record tender bid", fields: [choices("tender", "Published tender", "tenders", r => r.status === "published"), ...(role === "ps_admin" ? [choices("vendor", "Vendor", "vendors")] : []), field("amount", "Bid value (INR)", "number"), field("proposal", "Proposal and supporting references", "textarea")] };
    if (resource === "orders" && can("ps_admin")) return { ...base, title: "Create & issue purchase order", fields: [choices("indent", "Approved purchase request", "indents", r => ["authorized", "tender_selected"].includes(str(r.status))), choices("vendor", "Verified vendor", "vendors", r => Boolean(r.verified)), field("amount", "Approved total value (INR)", "number"), field("planned_delivery", "Expected delivery", "datetime-local")] };
    if (resource === "receipts" && can("employee", "department_admin", "department_head")) return { ...base, title: "Inspect delivery & record GRN", fields: [choices("indent", "Delivered request", "indents", r => ["delivered", "dispatched", "partial_received", "grn_recorded", "replacement_awaited"].includes(str(r.status))), field("accepted", "Accepted quantity", "number"), field("rejected", "Rejected quantity", "number"), field("inspection", "Inspection and condition", "textarea"), { ...field("evidence", "Evidence references (JSON list)", "json"), initial: "[]" }, { ...choices("replacement_case_id", "Replacement case (if applicable)", "cases", r => r.status === "replacement_awaited"), optional: true }] };
    if (resource === "cases" && can("employee", "department_admin", "department_head")) return { ...base, title: "Report discrepancy / request return", fields: [choices("indent", "Delivery", "indents"), fixed("kind", "Case type", ["damage", "shortage", "return", "replacement", "warranty"]), field("description", "Discrepancy description", "textarea"), { ...field("evidence", "Evidence references (JSON list)", "json"), initial: '["inspection reference"]' }] };
    if (resource === "invoices" && can("accounts")) return { ...base, title: "Record vendor invoice", fields: [choices("po", "Purchase order", "orders"), field("number", "Vendor invoice number"), field("quantity", "Invoiced quantity", "number"), field("amount", "Invoice amount (INR)", "number")] };
    if (resource === "reports" && can("ps_admin", "accounts", "auditor", "department_admin", "department_head")) return { ...base, title: "Generate authorized report", report: true, fields: [...reportFields, fixed("format", "Output format", ["screen", "csv"])] };
    if (resource === "schedules" && can("ps_admin", "accounts", "auditor", "department_admin", "department_head")) return { ...base, title: "Schedule report generation", fields: [...reportFields, field("interval_hours", "Repeat interval (hours)", "number"), field("next_run", "First generation", "datetime-local")] };
    if (resource === "policies" && can("ps_admin")) return { ...base, title: "Activate a procurement policy", fields: [field("name", "Unique policy version name"), { ...field("configuration", "Policy configuration (JSON)", "json"), initial: JSON.stringify(rows("policies").find(p => p.active)?.configuration || {}, null, 2) }] };
    return null;
  }
  const labelRef = (value: unknown) => {
    const text = str(value);
    for (const resource of ["indents", "stock", "vendors", "orders", "invoices"]) {
      const r = rows(resource).find(r => r.id === text);
      if (r) return str(r.item || r.name || r.number || shortId(r.id));
    }
    return shortId(value);
  };
  const display = (key: string, value: unknown) => {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (dateKeys.has(key)) return date(value);
    if (["amount", "estimated_cost"].includes(key)) return money(value);
    if (["indent", "vendor", "source", "po", "invoice"].includes(key)) return labelRef(value);
    if (typeof value === "object") return Array.isArray(value) ? value.map(v => typeof v === "object" ? JSON.stringify(v) : human(v)).join(" · ") || "None" : JSON.stringify(value);
    return human(value);
  };
  function table(resource: string, title?: string, compact = false) {
    const collection = rows(resource).filter(r => !search || JSON.stringify(r).toLowerCase().includes(search.toLowerCase()));
    const visible = compact ? collection.slice(0, 5) : collection.slice(page*10, page*10+10);
    return <section className="psm-panel" key={resource}>
      {title && <div className="psm-panel-head"><h2>{title}</h2><Badge variant="light" color="gray">{collection.length}</Badge>
        {createOperation(resource) && <Button variant="light" size="xs" onClick={() => show(createOperation(resource)!)}>Add {resource === "bids" ? "bid" : resource === "schedules" ? "schedule" : "record"}</Button>}</div>}
      <div className="psm-table-wrap"><table className="psm-table"><thead><tr><th>Reference</th>{(columns[resource] || []).map(([key, label]) => <th key={key}>{label}</th>)}<th><span className="psm-sr">Open record</span></th></tr></thead><tbody>
        {visible.map(r => <tr key={r.id}><td><button className="psm-ref" onClick={() => setSelected({ resource, row: r })}>#{shortId(r.id)}</button></td>{(columns[resource] || []).map(([key]) => <td key={key}>{key === "status" ? <Badge variant="light" color={color(r[key])}>{human(r[key])}</Badge> : <span title={display(key, r[key])}>{display(key, r[key])}</span>}</td>)}<td><Button variant="subtle" size="xs" aria-label={"Open "+shortId(r.id)} onClick={() => setSelected({ resource, row: r })}><FiArrowRight /></Button></td></tr>)}
        {!visible.length && <tr><td colSpan={(columns[resource]?.length || 0)+2}><div className="psm-empty"><FiArchive /><b>{search ? "No matching records" : "No records in your scope"}</b><p>{search ? "Try another item, status or reference." : "Records will appear here as the workflow progresses."}</p></div></td></tr>}
      </tbody></table></div>
      {!compact && collection.length > 10 && <Group justify="space-between" p="md"><Text size="sm">Showing {page*10+1}–{Math.min(page*10+10, collection.length)} of {collection.length}</Text><Group><Button size="xs" variant="default" disabled={!page} onClick={() => setPage(page-1)}>Previous</Button><Button size="xs" variant="default" disabled={(page+1)*10 >= collection.length} onClick={() => setPage(page+1)}>Next</Button></Group></Group>}
    </section>;
  }
  if (query.isPending) return <div className="psm-loading"><Loader /><Text>Loading your purchase and stores workspace…</Text></div>;
  if (query.isError || !data || !viewer) return <Alert color="red" title="Workspace unavailable">{errorMessage(query.error)}<Button variant="subtle" onClick={() => query.refetch()}>Try again</Button></Alert>;
  const nav = sections.filter(s => s.key !== "policies" || can("ps_admin")).filter(s => !["stock", "transfers"].includes(s.key) || can("department_admin", "department_head", "ps_admin", "accounts", "auditor", "final_authority", "committee"));
  const current = sections.find(s => s.key === tab)!;
  return <div className={"psm-root "+(preview ? "psm-standalone" : "")}>
    <aside className="psm-sidebar"><div className="psm-brand"><span className="psm-brand-icon"><FiPackage /></span><div><b>Fusion</b><small>Purchase & Stores</small></div></div>
      <div className="psm-sidebar-label">WORKSPACE</div><nav aria-label="Purchase and stores navigation">{nav.map(s => <button key={s.key} aria-current={tab === s.key ? "page" : undefined} className={tab === s.key ? "active" : ""} onClick={() => changeTab(s.key)}><s.icon /><span>{s.label}</span>{rows(s.key).length > 0 && <small>{rows(s.key).length}</small>}</button>)}</nav>
      <div className="psm-user"><span>{viewer.name.slice(0, 1)}</span><div><b>{human(role)}</b><small>{viewer.department} department</small></div></div>
    </aside>
    <main className="psm-main"><header className="psm-topbar"><span>Administration <span className="psm-divider">/</span> Purchase & Stores</span><Group gap="xs"><span className="psm-live">● Live workspace</span><Button aria-label="Refresh workspace" variant="subtle" color="gray" onClick={() => query.refetch()} loading={query.isFetching}><FiRefreshCw /></Button><Button aria-label="Notifications" variant="subtle" color="gray" onClick={() => changeTab("notifications")}><FiBell /></Button></Group></header>
      <div className="psm-content"><div className="psm-page-heading"><div><p className="psm-eyebrow">PURCHASE & STORES MANAGEMENT</p><h1>{tab === "dashboard" ? "Procurement overview" : current.label}</h1><p>{tab === "dashboard" ? "Every request, approval and delivery. One clear view." : "Authorized records and actions for your role and department."}</p></div>
        {createOperation(tab === "dashboard" ? "indents" : tab) && <Button color="teal" leftSection={<span>+</span>} onClick={() => show(createOperation(tab === "dashboard" ? "indents" : tab)!)}>{tab === "dashboard" || tab === "indents" ? "New purchase request" : tab === "reports" ? "Generate report" : "Create record"}</Button>}
      </div>
      {preview && <div className="psm-policy-note"><FiShield /><span>Preview uses synthetic records and an illustrative policy. Thresholds shown here are not institute rules.</span></div>}
      {tab === "dashboard" ? <>
        <div className="psm-metrics">{[
          ["Total requests", metrics?.requests, FiClipboard, "All requests within your scope", "teal"],
          ["In progress", metrics?.pending, FiClock, "Across review and fulfilment", "orange"],
          ["Awaiting receipt", metrics?.receipts_pending, FiPackage, "Ready for inspection / confirmation", "blue"],
          ["Open discrepancies", metrics?.open_cases, FiShield, "Final posting and payment are gated", "red"],
        ].map(([label, value, Icon, sub, tone]) => { const MetricIcon = Icon as typeof FiBox; return <button className="psm-metric" key={str(label)} onClick={() => changeTab(label === "Open discrepancies" ? "cases" : label === "Awaiting receipt" ? "receipts" : "indents")}><div><span>{str(label)}</span><MetricIcon className={"metric-icon "+str(tone)} /></div><b>{str(value ?? 0)}</b><small>{str(sub)}</small></button>; })}</div>
        <div className="psm-overview-grid"><div className="psm-primary-column">
          <section className="psm-panel psm-pipeline"><div className="psm-panel-head"><h2>From request to receipt</h2><Badge variant="light" color="teal">Workflow health</Badge></div><div className="psm-stages">{[
            ["Submitted", ["submitted", "modified"]], ["Review", ["external_required", "awaiting_approval", "stock_reserved"]],
            ["Procurement", ["authorized", "po_issued", "tender_published", "tender_selected"]], ["Receipt", ["delivered", "dispatched", "grn_recorded", "partial_received"]],
            ["Complete", ["completed", "paid"]],
          ].map(([name, states]) => <button key={str(name)} onClick={() => changeTab("indents")}><span>{rows("indents").filter(r => (states as string[]).includes(str(r.status))).length}</span><small>{str(name)}</small></button>)}</div></section>
          {table("indents", "Recent purchase requests", true)}
        </div><aside className="psm-secondary-column"><section className="psm-panel psm-focus"><div className="psm-panel-head"><h2>Your next actions</h2><FiCheckCircle /></div>
          {[...rows("indents")].sort((a,b) => Number(b.priority)-Number(a.priority) || Date.parse(str(a.created_at))-Date.parse(str(b.created_at))).flatMap(r => operations("indents", r).filter(o => o.action !== "repeat").map(o => ({ r, o }))).slice(0, 4).map(({ r, o }, i) => <button className="psm-task" key={r.id+i} onClick={() => show(o)}><span className="psm-task-icon"><FiClipboard /></span><span><b>{o.title}</b><small>{str(r.item)} · #{shortId(r.id)}</small></span><FiArrowRight /></button>)}
          {!rows("indents").some(r => operations("indents", r).some(o => o.action !== "repeat")) && <div className="psm-empty"><FiCheckCircle /><b>Your queue is clear</b><p>New tasks will appear when requests reach your role.</p></div>}
        </section><section className="psm-panel"><div className="psm-panel-head"><h2>Recent activity</h2><FiClock /></div><div className="psm-timeline">{rows("audit").slice(0, 5).map(a => <button key={a.id} onClick={() => setSelected({ resource: "audit", row: a })}><i /><span><b>{human(a.action)}</b><small>{human(a.entity)} · {date(a.created_at)}</small></span></button>)}</div></section>
        <div className="psm-help"><FiShield /><b>Controls built into every step</b><p>Stock is reserved before dispatch. Vendor verification, confirmed receipts and invoice matching protect payment release.</p></div></aside></div>
      </> : <>
        <div className="psm-toolbar"><TextInput aria-label="Search records" placeholder="Search item, status or reference…" leftSection={<FiSearch />} value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} /><Text size="sm" c="dimmed">Newest records · scoped to {human(role)}</Text></div>
        {table(tab)}
        {tab === "stock" && <div className="psm-subsection">{table("ledger", "Stock ledger")}</div>}
        {tab === "tenders" && <div className="psm-subsection">{table("bids", "Bids · sealed until the deadline")}</div>}
        {tab === "invoices" && <div className="psm-subsection">{table("payments", "Recorded payments")}</div>}
        {tab === "reports" && <div className="psm-subsection">{table("schedules", "Scheduled reports")}</div>}
        {tab === "cases" && <div className="psm-subsection">{table("communications", "Vendor communication history")}</div>}
      </>}
      <footer className="psm-footer">Fusion ERP · Purchase & Stores <span>Showing up to 200 recent records per section · {new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span></footer></div>
    </main>
    <Drawer opened={Boolean(selected)} onClose={() => setSelected(null)} title={selected ? human(selected.resource)+" · #"+shortId(selected.row.id) : ""} position="right" size="lg">
      {selected && <Stack><Group>{operations(selected.resource, selected.row).map((o, i) => <Button key={i} variant={i ? "light" : "filled"} color={o.action === "cancel" || o.action === "withdraw" ? "red" : "teal"} onClick={() => show(o)}>{o.title}</Button>)}</Group>
        <dl className="psm-details">{Object.entries(selected.row).filter(([key]) => key !== "policy_snapshot" && key !== "rows").map(([key, value]) => <div key={key}><dt>{human(key)}</dt><dd>{typeof value === "object" && value !== null ? <pre>{JSON.stringify(value, null, 2)}</pre> : display(key, value)}</dd></div>)}</dl>
        {["indents", "cases", "vendors"].includes(selected.resource) && <section><h3>Supporting documents</h3>
          {uploadError && <Alert color="red">{uploadError}</Alert>}
          {rows("attachments").filter(a => a.object_id === selected.row.id).map(a => <p key={a.id}><a href={"/api/v1/psm/attachments/"+a.id+"/download"} target="_blank" rel="noreferrer">{str(a.original_name)}</a></p>)}
          {can("employee", "department_admin", "department_head", "ps_admin") && (selected.resource !== "vendors" || role === "ps_admin") && <label className="psm-upload">Attach a document (up to 10 MiB)<input aria-label="Attach supporting document" type="file" onChange={async e => {
            const file = e.target.files?.[0]; if (!file || !selected) return; setUploadError("");
            const body = new FormData(); body.append("entity", selected.resource === "indents" ? "indent" : selected.resource === "cases" ? "case" : "vendor"); body.append("object_id", selected.row.id); body.append("file", file);
            try { await http.post("/psm/attachments/upload", body); await qc.invalidateQueries({ queryKey: ["psm"] }); } catch (err) { setUploadError(errorMessage(err)); }
          }} /></label>}
        </section>}
        {selected.resource === "vendors" && rows("vendor_history").some(v => v.vendor === selected.row.id) && <section><h3>Vendor master version history</h3>{rows("vendor_history").filter(v => v.vendor === selected.row.id).map(v => <details key={v.id}><summary>Version {str(v.version)} · {date(v.created_at)}</summary><pre>{JSON.stringify(v.snapshot, null, 2)}</pre></details>)}</section>}
        {selected.resource === "indents" && <><h3>Request history</h3>{rows("audit").filter(a => a.object_id === selected.row.id).map(a => <div key={a.id}><Badge color={color(a.action)}>{human(a.action)}</Badge><Text size="sm">{new Date(str(a.created_at)).toLocaleString("en-IN")}</Text><Text size="sm">Actor {str(a.actor_id)}</Text></div>)}</>}
        {selected.resource === "reports" && <div className="psm-report-output"><h3>Generated output</h3>{Array.isArray(selected.row.rows) && selected.row.rows.length > 0 ? <div className="psm-table-wrap"><table className="psm-table"><thead><tr>{Object.keys(selected.row.rows[0]).map(key => <th key={key}>{human(key)}</th>)}</tr></thead><tbody>{(selected.row.rows as Row[]).map((row, i) => <tr key={i}>{Object.entries(row).map(([key,value]) => <td key={key}>{display(key,value)}</td>)}</tr>)}</tbody></table></div> : <Text size="sm">No records matched the report criteria.</Text>}</div>}
      </Stack>}
    </Drawer>
    <Modal opened={Boolean(op)} onClose={() => !saving && setOp(null)} title={op?.title} size="lg" centered>
      <form onSubmit={e => { e.preventDefault(); submit(); }}><Stack>
        {error && <Alert role="alert" color="red" title="Action could not be completed">{error}</Alert>}
        {op?.fields.map(f => <div key={f.key}>{f.options ? <Select label={f.label} data={f.options} searchable clearable={f.optional} required={!f.optional} value={values[f.key] || null} onChange={v => setValues({ ...values, [f.key]: v || "" })} nothingFoundMessage="No eligible records in your scope" /> :
          f.type === "textarea" || f.type === "json" ? <Textarea label={f.label} required={!f.optional} autosize minRows={f.type === "json" ? 5 : 3} maxRows={15} value={values[f.key]} onChange={e => setValues({ ...values, [f.key]: e.target.value })} styles={f.type === "json" ? { input: { fontFamily: "monospace", fontSize: 13 } } : undefined} /> :
          f.type === "number" ? <NumberInput label={f.label} required={!f.optional} value={values[f.key]} decimalScale={3} onChange={v => setValues({ ...values, [f.key]: String(v) })} /> :
          <TextInput type={f.type || "text"} label={f.label} required={!f.optional} value={values[f.key]} onChange={e => setValues({ ...values, [f.key]: e.target.value })} />}</div>)}
        {!op?.fields.length && <Text>This action will update the record and retain an audit entry.</Text>}
        <Group justify="flex-end"><Button variant="default" onClick={() => setOp(null)} disabled={saving}>Back</Button><Button type="submit" color="teal" loading={saving}>{op?.report ? "Generate report" : "Confirm"}</Button></Group>
      </Stack></form>
    </Modal>
  </div>;
}
