import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";

export interface LeaveRequest { id:number; user_id:number; category:string; start_date:string; end_date:string; half:string; days:string; reason:string; station_leave_details:string; substitute_user_id:number|null; substitute_status:string; status:string; decision:string; decision_note:string; created_at:string; }
export interface Balance { id:number; year:number; category:string; entitled:string; used:string; carried_forward:string; available:string; }
const key=["elm"];
export function useLeaves(){return useQuery({queryKey:[...key,"leaves"],queryFn:async()=> (await http.get<LeaveRequest[]>("/elm/leaves")).data});}
export function useBalances(){return useQuery({queryKey:[...key,"balances"],queryFn:async()=> (await http.get<Balance[]>("/elm/leaves/balances")).data});}
export function useCreateLeave(){const qc=useQueryClient();return useMutation({mutationFn:async(b:Record<string,unknown>)=>(await http.post<LeaveRequest>("/elm/leaves",b)).data,onSuccess:()=>qc.invalidateQueries({queryKey:key})});}
export function useSubmitLeave(){const qc=useQueryClient();return useMutation({mutationFn:async(id:number)=>(await http.post<LeaveRequest>(`/elm/leaves/${id}/submit`,{})).data,onSuccess:()=>qc.invalidateQueries({queryKey:key})});}
export function useWithdrawLeave(){const qc=useQueryClient();return useMutation({mutationFn:async(id:number)=>(await http.post<LeaveRequest>(`/elm/leaves/${id}/withdraw`,{})).data,onSuccess:()=>qc.invalidateQueries({queryKey:key})});}
export function useReviews(){return useQuery({queryKey:[...key,"reviews"],queryFn:async()=> (await http.get<LeaveRequest[]>("/elm/reviews")).data});}
export function useReview(){const qc=useQueryClient();return useMutation({mutationFn:async(a:{id:number;action:string;note?:string})=>(await http.post<LeaveRequest>(`/elm/reviews/${a.id}`,a)).data,onSuccess:()=>qc.invalidateQueries({queryKey:key})});}
export function usePolicies(){return useQuery({queryKey:[...key,"policies"],queryFn:async()=> (await http.get("/elm/admin/policies")).data});}
export function useHolidays(){return useQuery({queryKey:[...key,"holidays"],queryFn:async()=> (await http.get("/elm/admin/holidays")).data});}
