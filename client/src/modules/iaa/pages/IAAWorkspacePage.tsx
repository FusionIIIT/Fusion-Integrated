import {
 Alert,Badge,Button,Card,Divider,Group,NumberInput,Select,SimpleGrid,Stack,
 Table,Text,TextInput,Textarea,Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { errorMessage,http } from "../../../lib/http";
import { useActiveIaaRole,useIaaMutation,useIaaQuery } from "../api/hooks";
import type { Page,FinancialRecord,ApprovalStep,Anomaly,AuditObservation,IaaNotification,ReportSummary } from "../api/types";

type Section="requests"|"ta"|"finance"|"approvals"|"anomalies"|"observations"|"reports"|"notifications"|"configuration";
const TITLES:Record<Section,string>={
 requests:"Expense / Voucher Requests",ta:"Travel Allowance",finance:"Finance Review Queue",
 approvals:"Approval Queue",anomalies:"Anomaly Management",observations:"Audit Observations",
 reports:"Reports & Dashboards",notifications:"Notifications",configuration:"IAA Configuration"
};
const ENDPOINT:Record<Exclude<Section,"configuration">,string>={
 requests:"/iaa/requests",ta:"/iaa/ta",finance:"/iaa/finance/queue",approvals:"/iaa/approvals",
 anomalies:"/iaa/anomalies",observations:"/iaa/observations",reports:"/iaa/reports",notifications:"/iaa/notifications"
};
function Status({value}:{value:string}){
 const color=["approved","verified","recorded","resolved","closed"].includes(value)?"green":
  ["rejected","escalated","open","anomaly_pending"].includes(value)?"orange":"blue";
 return <Badge color={color} variant="light">{value.replaceAll("_"," ")}</Badge>;
}
function RecordTable({rows,onSubmit,onRecord}:{rows:FinancialRecord[];onSubmit?:(r:FinancialRecord)=>void;onRecord?:(r:FinancialRecord)=>void}){
 if(!rows.length)return <Text c="dimmed">No records found.</Text>;
 return <Table striped highlightOnHover withTableBorder>
  <Table.Thead><Table.Tr><Table.Th>ID</Table.Th><Table.Th>Type</Table.Th><Table.Th>Department</Table.Th><Table.Th>Amount</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
  <Table.Tbody>{rows.map(r=><Table.Tr key={r.id}>
   <Table.Td>#{r.id}</Table.Td><Table.Td>{r.request_type}</Table.Td><Table.Td>{r.department}</Table.Td>
   <Table.Td>{r.amount}</Table.Td><Table.Td><Status value={r.status}/></Table.Td>
   <Table.Td><Group gap="xs">
    {r.status==="draft"&&onSubmit&&<Button size="xs" onClick={()=>onSubmit(r)}>Submit</Button>}
    {(r.status==="approved"||r.status==="verified")&&onRecord&&<Button size="xs" variant="light" onClick={()=>onRecord(r)}>Process / Record</Button>}
   </Group></Table.Td>
  </Table.Tr>)}</Table.Tbody>
 </Table>;
}
function Problem({message}:{message:string}){
 return <Alert color="red" title="IAA request could not be completed">{message}</Alert>;
}
export function IAAWorkspacePage({section}:{section:Section}){
 const role=useActiveIaaRole();
 const mutation=useIaaMutation();
 const data=useIaaQuery<Page<FinancialRecord>|Page<ApprovalStep>|Page<Anomaly>|Page<AuditObservation>|Page<IaaNotification>|ReportSummary>(
  section,ENDPOINT[section as Exclude<Section,"configuration">]??"/iaa/reports",section!=="configuration");
 const [requestType,setRequestType]=useState("");
 const [department,setDepartment]=useState("");
 const [amount,setAmount]=useState<number|string>("");
 const [description,setDescription]=useState("");
 const [tripStart,setTripStart]=useState("");
 const [tripEnd,setTripEnd]=useState("");
 const [tripPurpose,setTripPurpose]=useState("");
 const [remarks,setRemarks]=useState("");
 const [recordId,setRecordId]=useState<number|string>("");
 const [documentRecordId,setDocumentRecordId]=useState<number|string>("");
 const [documentName,setDocumentName]=useState("");
 const [storageReference,setStorageReference]=useState("");
 const [queryQuestion,setQueryQuestion]=useState("");
 const [observationKind,setObservationKind]=useState("expense_voucher");
 const [highValueThreshold,setHighValueThreshold]=useState<number|string>("");
 const [assignmentUserId,setAssignmentUserId]=useState<number|string>("");
 const [assignmentRole,setAssignmentRole]=useState("finance_staff");
 const [category,setCategory]=useState("policy_violation");
 const [details,setDetails]=useState("");
 const [observationTitle,setObservationTitle]=useState("");
 const [observationDetails,setObservationDetails]=useState("");
 const [responseText,setResponseText]=useState("");
 const [evidenceReference,setEvidenceReference]=useState("");
 const [financialYear,setFinancialYear]=useState("2026-27");
 const [fyStart,setFyStart]=useState("2026-04-01");
 const [fyEnd,setFyEnd]=useState("2027-03-31");
 const [budget,setBudget]=useState<number|string>("");
 const [approvalRole,setApprovalRole]=useState("hod");
 const [timeoutHours,setTimeoutHours]=useState<number|string>(24);

 const send=(path:string,payload:Record<string,unknown>={},message="IAA change saved")=>{
  mutation.mutate({path,payload},{
   onSuccess:()=>notifications.show({color:"green",message}),
   onError:(error)=>notifications.show({color:"red",message:errorMessage(error)}),
  });
 };
 const rows=(data.data as Page<FinancialRecord>|undefined)?.results??[];
 const submitRecord=(r:FinancialRecord)=>send(
  r.record_kind==="ta"?`/iaa/ta/${r.id}/submit`:`/iaa/requests/${r.id}/submit`,{},"Request submitted");
 const recordApproved=(r:FinancialRecord)=>send(`/iaa/requests/${r.id}/record`,{},"Internal record completed");
 const createDraft=()=>{
  const payload:Record<string,unknown>={request_type:requestType,department,amount:Number(amount),description};
  if(section==="ta")Object.assign(payload,{trip_start_date:tripStart,trip_end_date:tripEnd,trip_purpose:tripPurpose});
  send(section==="ta"?"/iaa/ta":"/iaa/requests",payload,"Draft saved");
 };

 return <Stack gap="md">
  <Group justify="space-between" align="flex-start">
   <div><Title order={2}>{TITLES[section]}</Title><Text c="dimmed" size="sm">Internal Audit and Accounts · Fusion ERP</Text></div>
   {role.data&&<Select label="Active Fusion role" w={230} value={role.data.active_role}
    data={role.data.available_roles.map(x=>({value:x,label:x}))}
    onChange={value=>value&&send("/iaa/roles/active",{role:value},"Active role changed; refreshing Fusion session")}/>}
  </Group>
  {data.isError&&<Problem message="Check the active Fusion role and its IAA permission grant."/>}

  {(section==="requests"||section==="ta")&&<>
   <Card withBorder>
    <Title order={4}>Create {section==="ta"?"TA claim":"expense / voucher draft"}</Title>
    <Text size="sm" c="dimmed">Drafts may be incomplete. Submission checks required fields and configured evidence requirements.</Text>
    <SimpleGrid cols={{base:1,sm:2}} mt="sm">
     <TextInput label="Request type" value={requestType} onChange={e=>setRequestType(e.currentTarget.value)} required/>
     <TextInput label="Department" value={department} onChange={e=>setDepartment(e.currentTarget.value)} required/>
     <NumberInput label="Amount" min={0} decimalScale={2} value={amount} onChange={setAmount}/>
     <TextInput label="Description" value={description} onChange={e=>setDescription(e.currentTarget.value)}/>
     {section==="ta"&&<>
      <TextInput type="date" label="Trip start" value={tripStart} onChange={e=>setTripStart(e.currentTarget.value)}/>
      <TextInput type="date" label="Trip end" value={tripEnd} onChange={e=>setTripEnd(e.currentTarget.value)}/>
      <TextInput label="Trip purpose" value={tripPurpose} onChange={e=>setTripPurpose(e.currentTarget.value)}/>
     </>}
    </SimpleGrid>
    <Group justify="flex-end" mt="md"><Button onClick={createDraft} loading={mutation.isPending}>Save draft</Button></Group>
   </Card>
   {!data.isError&&<RecordTable rows={rows} onSubmit={submitRecord} onRecord={recordApproved}/>}
   <Card withBorder>
    <Title order={4}>Attach a supporting document reference</Title>
    <Text size="sm" c="dimmed">First save a draft. Supply a file reference issued by the configured Fusion storage service.</Text>
    <SimpleGrid cols={{base:1,sm:2}} mt="sm">
     <NumberInput label="Draft record ID" min={1} value={documentRecordId} onChange={setDocumentRecordId}/>
     <TextInput label="Document name" value={documentName} onChange={e=>setDocumentName(e.currentTarget.value)}/>
     <TextInput label="Storage reference" value={storageReference} onChange={e=>setStorageReference(e.currentTarget.value)}/>
    </SimpleGrid>
    <Button mt="sm" onClick={()=>send(`/iaa/requests/${Number(documentRecordId)}/attachments`,{name:documentName,storage_reference:storageReference},"Supporting document attached")}>Attach reference</Button>
   </Card>
  </>}

  {section==="finance"&&((data.data as Page<FinancialRecord>|undefined)?.results??[]).map(r=><Card withBorder key={r.id}>
   <Group justify="space-between"><Text fw={600}>Request #{r.id} · {r.request_type}</Text><Status value={r.status}/></Group>
   <Text size="sm">{r.department} · {r.amount} · {r.record_kind}</Text>
   <Textarea label="Finance remarks / policy rejection reason" value={remarks} onChange={e=>setRemarks(e.currentTarget.value)} mt="sm"/>
   <Textarea label="Clarification question (optional)" value={queryQuestion} onChange={e=>setQueryQuestion(e.currentTarget.value)} mt="sm"/>
   <Group justify="flex-end" mt="sm">
    <Button variant="light" disabled={!queryQuestion.trim()} onClick={()=>send(`/iaa/requests/${r.id}/queries`,{question:queryQuestion},"Clarification sent")}>Request clarification</Button>
    <Button color="red" variant="light" onClick={()=>send(`/iaa/finance/requests/${r.id}/validate`,{policy_passed:false,remarks},"Request rejected after Finance review")}>Reject</Button>
    <Button onClick={()=>send(`/iaa/finance/requests/${r.id}/validate`,{policy_passed:true,remarks},"Finance validation completed")}>Validate / Route</Button>
   </Group>
  </Card>)}

  {section==="approvals"&&((data.data as Page<ApprovalStep>|undefined)?.results??[]).map(step=><Card withBorder key={step.id}>
   <Group justify="space-between"><Text fw={600}>Approval #{step.id} · {step.authority_role}</Text><Status value={step.status}/></Group>
   <Text size="sm">Record #{step.record_id} · Level {step.step_number} · Due {step.due_at??"No timeout configured"}</Text>
   <Textarea label="Mandatory approval/rejection remarks" value={remarks} onChange={e=>setRemarks(e.currentTarget.value)} mt="sm"/>
   <Group justify="flex-end" mt="sm">
    <Button color="red" variant="light" onClick={()=>send(`/iaa/approvals/${step.id}/decision`,{decision:"reject",remarks},"Approval rejected")}>Reject</Button>
    <Button onClick={()=>send(`/iaa/approvals/${step.id}/decision`,{decision:"approve",remarks},"Approval recorded")}>Approve</Button>
   </Group>
  </Card>)}

  {section==="anomalies"&&<>
   <Card withBorder><Title order={4}>Flag material anomaly</Title>
    <NumberInput label="Related financial record ID" value={recordId} onChange={setRecordId} min={1}/>
    <TextInput label="Category" value={category} onChange={e=>setCategory(e.currentTarget.value)} mt="sm"/>
    <Textarea label="Details and supporting context" value={details} onChange={e=>setDetails(e.currentTarget.value)} mt="sm"/>
    <Button mt="sm" onClick={()=>send("/iaa/anomalies",{record_id:Number(recordId),category,details,severity:"medium"},"Anomaly flagged")}>Flag anomaly</Button>
   </Card>
   {((data.data as Page<Anomaly>|undefined)?.results??[]).map(a=><Card withBorder key={a.id}>
    <Group justify="space-between"><Text fw={600}>#{a.id} · {a.title}</Text><Status value={a.status}/></Group>
    <Text size="sm">{a.details} · Resolver: {a.resolver_role}</Text>
    <Textarea label="Resolution / escalation remarks" value={remarks} onChange={e=>setRemarks(e.currentTarget.value)} mt="sm"/>
    <Group justify="flex-end" mt="sm">
     <Button variant="light" onClick={()=>send(`/iaa/anomalies/${a.id}/resolve`,{action:"escalate",resolution:remarks},"Anomaly escalated")}>Escalate</Button>
     <Button onClick={()=>send(`/iaa/anomalies/${a.id}/resolve`,{action:"resolve",resolution:remarks},"Anomaly resolved")}>Resolve</Button>
    </Group>
   </Card>)}
  </>}

  {section==="observations"&&<>
   <Card withBorder><Title order={4}>Raise audit observation</Title>
    <NumberInput label="Financial record ID" value={recordId} onChange={setRecordId} min={1}/>
    <Select label="Record type" value={observationKind} onChange={v=>v&&setObservationKind(v)} data={[{value:"expense_voucher",label:"Expense / Voucher"},{value:"ta",label:"Travel Allowance"}]} mt="sm"/>
    <TextInput label="Observation title" value={observationTitle} onChange={e=>setObservationTitle(e.currentTarget.value)} mt="sm"/>
    <Textarea label="Observation details" value={observationDetails} onChange={e=>setObservationDetails(e.currentTarget.value)} mt="sm"/>
    <Button mt="sm" onClick={()=>send("/iaa/observations",{record_kind:observationKind,record_id:Number(recordId),title:observationTitle,details:observationDetails},"Observation raised")}>Raise observation</Button>
   </Card>
   {((data.data as Page<AuditObservation>|undefined)?.results??[]).map(o=><Card withBorder key={o.id}>
    <Group justify="space-between"><Text fw={600}>#{o.id} · {o.title}</Text><Status value={o.status}/></Group>
    <Text size="sm">{o.details}</Text>
    {o.status==="open"&&<Stack mt="sm">
     <Textarea label="Corrective action response" value={responseText} onChange={e=>setResponseText(e.currentTarget.value)}/>
     <TextInput label="Supporting evidence reference" value={evidenceReference} onChange={e=>setEvidenceReference(e.currentTarget.value)}/>
     <Button onClick={()=>send(`/iaa/observations/${o.id}/respond`,{response_text:responseText,evidence_references:[evidenceReference]},"Observation response submitted")}>Submit response</Button>
    </Stack>}
    {o.status==="responded"&&<Group justify="flex-end" mt="sm">
     <Button color="red" variant="light" onClick={()=>send(`/iaa/observations/${o.id}/verify`,{satisfactory:false,remarks:"Further corrective action required."},"Observation returned to Open")}>Return to Open</Button>
     <Button onClick={()=>send(`/iaa/observations/${o.id}/verify`,{satisfactory:true,remarks:"Corrective action and evidence verified."},"Observation closed")}>Verify & Close</Button>
    </Group>}
   </Card>)}
  </>}

  {section==="reports"&&(()=>{
   const r=data.data as ReportSummary|undefined;
   return <><SimpleGrid cols={{base:1,sm:2,md:3}}>
    {[
     ["Total records",r?.total_records],["Total anomalies",r?.total_anomalies],["Open anomalies",r?.open_anomalies],
     ["Total observations",r?.total_observations],["Open observations",r?.open_observations],
     ["Average approval hours",r?.average_approval_turnaround_hours??"—"]
    ].map(([label,value])=><Card withBorder key={String(label)}><Text c="dimmed" size="sm">{label}</Text><Title order={3}>{value??"—"}</Title></Card>)}
   </SimpleGrid>
   <Button onClick={()=>void http.get("/iaa/reports/export.csv",{responseType:"blob"}).then(res=>{
    const url=URL.createObjectURL(res.data);const a=document.createElement("a");a.href=url;a.download="iaa-report.csv";a.click();URL.revokeObjectURL(url);
   }).catch(error=>notifications.show({color:"red",message:errorMessage(error)}))}>Export CSV</Button>
   <Divider/><Title order={4}>Status breakdown</Title>
   {Object.entries(r?.record_status_counts??{}).map(([s,n])=><Group justify="space-between" key={s}><Text>{s.replaceAll("_"," ")}</Text><Text fw={600}>{n}</Text></Group>)}
   </>;
  })()}

  {section==="notifications"&&((data.data as Page<IaaNotification>|undefined)?.results??[]).map(n=><Card withBorder key={n.id}>
   <Group justify="space-between"><Text fw={600}>{n.title}</Text>{n.read_at?<Badge color="gray">Read</Badge>:<Badge color="blue">Unread</Badge>}</Group>
   <Text size="sm">{n.message}</Text>
   {!n.read_at&&<Button size="xs" mt="sm" onClick={()=>send(`/iaa/notifications/${n.id}/read`,{},"Notification marked read")}>Mark read</Button>}
  </Card>)}

  {section==="configuration"&&<>
   <Card withBorder><Title order={4}>Financial-year configuration</Title>
    <TextInput label="Financial year" value={financialYear} onChange={e=>setFinancialYear(e.currentTarget.value)}/>
    <SimpleGrid cols={2} mt="sm"><TextInput type="date" label="Starts on" value={fyStart} onChange={e=>setFyStart(e.currentTarget.value)}/>
     <TextInput type="date" label="Ends on" value={fyEnd} onChange={e=>setFyEnd(e.currentTarget.value)}/></SimpleGrid>
    <NumberInput label="High-value TA approval threshold" min={0} value={highValueThreshold} onChange={setHighValueThreshold} mt="sm"/>
    <Text size="xs" c="dimmed">This value must come from the institution's policy. Leave blank until it is configured.</Text>
    <Button mt="sm" onClick={()=>send("/iaa/admin/financial-years",{financial_year:financialYear,starts_on:fyStart,ends_on:fyEnd,settings:{budget_required:true,ta_high_value_threshold:Number(highValueThreshold)||null,ta_policy:{documents_required:true},anomaly_resolvers:{policy_violation:"auditor",budget_shortfall:"finance_staff"}},is_active:true},"Financial year configuration saved")}>Save financial year</Button>
   </Card>
   <Card withBorder><Title order={4}>Departmental budget</Title>
    <TextInput label="Department" value={department} onChange={e=>setDepartment(e.currentTarget.value)}/>
    <NumberInput label="Allocated budget" min={0} value={budget} onChange={setBudget} mt="sm"/>
    <Button mt="sm" onClick={()=>send("/iaa/admin/budgets",{department,financial_year:financialYear,allocated:Number(budget),spent:0,committed:0,is_active:true},"Departmental budget saved")}>Save budget</Button>
   </Card>
   <Card withBorder><Title order={4}>Approval hierarchy rule</Title>
    <Select label="First approval authority" value={approvalRole} onChange={v=>v&&setApprovalRole(v)}
     data={[{value:"hod",label:"HoD"},{value:"dean",label:"Dean"},{value:"director",label:"Director"}]}/>
    <NumberInput label="Timeout hours" min={1} value={timeoutHours} onChange={setTimeoutHours} mt="sm"/>
    <Button mt="sm" onClick={()=>send("/iaa/admin/approval-rules",{record_kind:"",request_type:"",department:"",min_amount:null,max_amount:null,levels:[{role:approvalRole,timeout_hours:Number(timeoutHours)}],priority:100,is_active:true},"Approval route configured")}>Save approval route</Button>
   </Card>
   <Card withBorder><Title order={4}>Record IAA role assignment</Title>
    <NumberInput label="IAM user ID" min={1} value={assignmentUserId} onChange={setAssignmentUserId}/>
    <Select label="IAA role" value={assignmentRole} onChange={v=>v&&setAssignmentRole(v)} mt="sm"
     data={[{value:"finance_staff",label:"Finance Staff"},{value:"hod",label:"HoD"},{value:"dean",label:"Dean"},{value:"director",label:"Director"},{value:"auditor",label:"Auditor"},{value:"basic_user",label:"Basic User"}]}/>
    <Button mt="sm" onClick={()=>send("/iaa/admin/roles",{user_id:Number(assignmentUserId),role:assignmentRole,is_active:true},"IAA role assignment recorded")}>Record assignment</Button>
   </Card>
   <Alert color="blue" title="Role administration requires IAM provisioning">
    IAA records assignment changes for its local workflow configuration. Effective Fusion role grants are controlled by IAM; the current Fusion IAM client does not expose a role-grant mutation endpoint.
   </Alert>
  </>}

  <Divider/><Text size="xs" c="dimmed">IAA tracks internal governance and audit records only. Process/Record does not transfer money or execute payment.</Text>
 </Stack>;
}
