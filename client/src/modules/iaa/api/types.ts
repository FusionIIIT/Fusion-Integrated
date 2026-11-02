export type IaaStatus="draft"|"submitted"|"query_raised"|"query_responded"|"finance_validated"|"verified"|"approval_pending"|"escalated"|"anomaly_pending"|"approved"|"rejected"|"recorded";
export interface Page<T>{count:number;results:T[]}
export interface FinancialRecord{id:number;record_kind:"expense_voucher"|"ta";request_type:string;created_by_id:number;department:string;amount:string;description:string;status:IaaStatus;financial_year:string;trip_start_date?:string|null;trip_end_date?:string|null;trip_purpose?:string;created_at:string}
export interface ApprovalStep{id:number;record_id:number;step_number:number;authority_role:string;assigned_user_id?:number|null;status:string;due_at?:string|null;remarks:string}
export interface Anomaly{id:number;record_id:number;category:string;severity:string;title:string;details:string;status:"open"|"resolved"|"escalated";resolver_role:string;resolution:string}
export interface AuditObservation{id:number;record_kind:string;record_id:number;title:string;details:string;status:"open"|"responded"|"closed";concerned_user_id?:number|null;responses?:{id:number;response_text:string;evidence_references:string[]}[]}
export interface IaaNotification{id:number;event_type:string;title:string;message:string;read_at?:string|null;created_at:string}
export interface ReportSummary{total_records:number;record_status_counts:Record<string,number>;total_anomalies:number;open_anomalies:number;total_observations:number;open_observations:number;average_approval_turnaround_hours:number|null}
