import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {http} from "../../../lib/http";
export function useIaaQuery<T>(section:string,path:string,enabled=true){
 return useQuery<T>({queryKey:["iaa",section],queryFn:async()=>(await http.get<T>(path)).data,enabled});
}
export function useIaaMutation(){
 const qc=useQueryClient();
 return useMutation({
  mutationFn:async({path,payload={},method="post"}:{path:string;payload?:Record<string,unknown>;method?:"post"|"patch"})=>
   (await http.request({url:path,method,data:payload})).data,
  onSuccess:()=>qc.invalidateQueries({queryKey:["iaa"]}),
 });
}
export function useActiveIaaRole(){
 return useQuery<{active_role:string;available_roles:string[]}>({
  queryKey:["iaa","active-role"],queryFn:async()=>(await http.get("/iaa/roles/active")).data,
 });
}
