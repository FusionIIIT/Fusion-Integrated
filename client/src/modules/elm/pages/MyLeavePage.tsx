import { useState } from "react";
import { Alert, Button, Card, Container, Group, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { http, errorMessage } from "../../../lib/http";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { LeaveRequest } from "../api/types";
const categories = ["CL","RH","SCL","EL","COL","VL"].map(x=>({value:x,label:x}));
export default function MyLeavePage(){
 const [category,setCategory]=useState<string|null>("CL"),[start,setStart]=useState(""),[end,setEnd]=useState(""),[purpose,setPurpose]=useState(""),[substitute,setSubstitute]=useState("");
 const qc=useQueryClient();
 const query=useQuery({queryKey:["elm","mine"],queryFn:async()=> (await http.get<LeaveRequest[]>("/elm/mine")).data});
 const apply=useMutation({mutationFn:async()=> (await http.post<LeaveRequest>("/elm/apply",{category,start_date:start,end_date:end,purpose,substitute_user_id: substitute?Number(substitute):null})).data,onSuccess:()=>{notifications.show({title:"Leave request submitted",message:"Your request has been recorded."});setPurpose("");qc.invalidateQueries({queryKey:["elm"]});},onError:e=>notifications.show({title:"Could not submit",message:errorMessage(e),color:"red"})});
 const action=useMutation({mutationFn:async({id,action}:{id:number;action:string})=>(await http.post(`/elm/requests/${id}/action`,{action})).data,onSuccess:()=>qc.invalidateQueries({queryKey:["elm"]}),onError:e=>notifications.show({title:"Action failed",message:errorMessage(e),color:"red"})});
 return <Container size="xl"><Stack>
 <Title order={2}>Employee Leave Management</Title><Text c="dimmed">Apply for leave and review your request history.</Text>
 <Card withBorder><Stack><Title order={3}>Apply for leave</Title><Select label="Leave category" data={categories} value={category} onChange={setCategory} required/><Group grow><TextInput type="date" label="From" value={start} onChange={e=>setStart(e.currentTarget.value)}/><TextInput type="date" label="To" value={end} onChange={e=>setEnd(e.currentTarget.value)}/></Group><TextInput label="Substitute user ID (if required)" value={substitute} onChange={e=>setSubstitute(e.currentTarget.value)} placeholder="IAM user ID"/><Textarea label="Purpose / reason" value={purpose} onChange={e=>setPurpose(e.currentTarget.value)} minRows={3} required/><Button loading={apply.isPending} disabled={!category||!start||!end||!purpose.trim()} onClick={()=>apply.mutate()}>Submit leave request</Button></Stack></Card>
 <Card withBorder>
  <Stack>
    <Title order={3}>My leave requests</Title>

    {query.error && (
      <Alert color="red">
        Unable to load leave requests.
      </Alert>
    )}

    <Table.ScrollContainer minWidth={700}>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Category</Table.Th>
            <Table.Th>Dates</Table.Th>
            <Table.Th>Days</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Action</Table.Th>
          </Table.Tr>
        </Table.Thead>

        <Table.Tbody>
          {(query.data ?? []).map((r) => (
            <Table.Tr key={r.id}>
              <Table.Td>{r.category}</Table.Td>
              <Table.Td>
                {r.start_date} – {r.end_date}
              </Table.Td>
              <Table.Td>{r.days}</Table.Td>
              <Table.Td>
                {r.status.replaceAll("_", " ")}
              </Table.Td>
              <Table.Td>
                {r.status.startsWith("awaiting_") ||
                r.status === "applicant_action_required" ? (
                  <Button
                    size="xs"
                    variant="light"
                    color="red"
                    onClick={() =>
                      action.mutate({
                        id: r.id,
                        action: "withdraw",
                      })
                    }
                  >
                    Withdraw
                  </Button>
                ) : (
                  "—"
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  </Stack>
</Card>
 </Stack></Container>;
}
