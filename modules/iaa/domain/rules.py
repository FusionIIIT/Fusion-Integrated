"""Pure IAA policy rules; no Django dependencies."""
from dataclasses import dataclass
from decimal import Decimal,InvalidOperation
@dataclass(frozen=True)
class ValidationIssue:
 field:str; code:str; message:str
def dec(v):
 try:return Decimal(str(v))
 except (InvalidOperation,TypeError,ValueError):return None
def submission_errors(p,*,kind="expense_voucher",attachment_count=0,required_documents=False):
 out=[]
 for f,label in (("request_type","Request type"),("department","Department"),("description","Description")):
  if not str(p.get(f,"") or "").strip():out.append(ValidationIssue(f,"required",f"{label} is required."))
 a=dec(p.get("amount"))
 if a is None or a<=0:out.append(ValidationIssue("amount","positive_amount","Amount must be positive."))
 if kind=="ta":
  start,end=p.get("trip_start_date"),p.get("trip_end_date")
  if not start:out.append(ValidationIssue("trip_start_date","required","Trip start date is required."))
  if not end:out.append(ValidationIssue("trip_end_date","required","Trip end date is required."))
  if start and end and end<start:out.append(ValidationIssue("trip_end_date","date_order","Trip end cannot precede trip start."))
  if not str(p.get("trip_purpose","") or "").strip():out.append(ValidationIssue("trip_purpose","required","Trip purpose is required."))
 if required_documents and int(attachment_count or 0)<1:out.append(ValidationIssue("attachments","required","A supporting document is required."))
 return out
def budget_shortfall(*,amount,allocated,spent,committed=Decimal("0")):
 xs=[dec(x) for x in (amount,allocated,spent,committed)]
 if any(x is None for x in xs):raise ValueError("Budget inputs must be decimal values.")
 a,b,c,d=xs
 return max(Decimal("0"),c+d+a-b)
def may_approve(*,creator_id,actor_id):
 return creator_id is not None and actor_id is not None and int(creator_id)!=int(actor_id)
def select_approval_rule(rows,*,kind,request_type,department,amount):
 a=dec(amount)
 if a is None:return None
 eligible=[]
 for r in rows:
  if not r.get("is_active",True):continue
  if r.get("record_kind") and r["record_kind"]!=kind:continue
  if r.get("request_type") and r["request_type"].casefold()!=request_type.casefold():continue
  if r.get("department") and r["department"].casefold()!=department.casefold():continue
  lo=dec(r.get("min_amount")) if r.get("min_amount") is not None else None
  hi=dec(r.get("max_amount")) if r.get("max_amount") is not None else None
  if lo is not None and a<lo:continue
  if hi is not None and a>hi:continue
  rank=sum(bool(r.get(k)) for k in ("record_kind","request_type","department"))+int(lo is not None)+int(hi is not None)
  eligible.append((rank,int(r.get("priority",100)),r))
 if not eligible:return None
 eligible.sort(key=lambda x:(-x[0],x[1]))
 return eligible[0][2]
def may_close_observation(*,satisfactory,has_response,has_evidence):
 return bool(satisfactory and has_response and has_evidence)
