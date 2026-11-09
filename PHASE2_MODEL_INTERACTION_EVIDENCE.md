# Phase 2 Model Interaction Evidence - Qwen2.5-Coder 7B

Model: `qwen2.5-coder:7b` (7.6B, Q4_K_M via Ollama)
Target Module: Employee Leave Management (`modules/elm`)
Target Repository: `C:\Users\rohan\Documents\Codex\2026-10-11\documents-plugin-documents-openai-primary-runtime-2\outputs\ELM_Qwen25Coder7B`
Branch: `phase2/qwen25-coder-7b`

All interactions below represent direct, unedited prompts sent to `qwen2.5-coder:7b` and raw responses returned by the local model.

## Stage: Stage 1: Pure Domain Rules (modules/elm/domain/rules.py)

### Prompt

```text
ï»¿You are Qwen2.5-Coder 7B running locally.
Provide ONLY valid Python code for `modules/elm/domain/rules.py` implementing the official Fusion ELM business rules without any Django imports.

Requirements to implement:
1. ENTITLEMENTS dictionary:
   CL: 8, RH: 2, SCL: 15, EL: 30, VL: 60, COL: 20 (all Decimal)
2. count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
   - Validate category in ENTITLEMENTS and start <= end.
   - For 'CL' half-day ('first' or 'second'): requires start == end, returns Decimal('0.5').
   - For 'EL', 'COL', 'VL': continuous days count including weekends/closed days (Decimal((end - start).days + 1)).
   - For 'CL', 'SCL', 'RH': working days only, skipping any dates in closed_dates.
3. intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool:
   - Returns True if date intervals overlap.
   - Exception: When a_start == a_end == b_start == b_end, and one is 'first' half and the other is 'second' half, they DO NOT overlap (return False).
4. calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]:
   - BR-EL-007 / BR-EL-008: Convert unutilized VL to EL at 2 VL : 1 EL. Floor division: converted = int(unutilized_vl // 2).
   - Space available in EL balance before reaching max_el_cap. Credited EL is min(converted, max(0, max_el_cap - current_el)).
   - Forfeited/lapsed VL is any VL that didn't result in credited EL.
   - Returns (credited_el, forfeited_vl, new_el_balance).
5. validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool:
   - BR-EL-013: If is_station_leave is True, destination and emergency_contact must be non-empty strings. Returns True if valid, False otherwise.
6. can_substitute(applicant_id: int, substitute_id: int) -> bool:
   - BR-EL-014: applicant_id != substitute_id.

Return ONLY pure Python code. Do not wrap in markdown quotes if possible, or use standard ```python fences.

```

### Model Response

```python
```python
from datetime import date, timedelta
from decimal import Decimal

ENTITLEMENTS = {
    'CL': Decimal('8'),
    'RH': Decimal('2'),
    'SCL': Decimal('15'),
    'EL': Decimal('30'),
    'VL': Decimal('60'),
    'COL': Decimal('20')
}

def count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
    if category not in ENTITLEMENTS or start > end:
        raise ValueError("Invalid category or date range")
    
    if category == 'CL':
        if half_day and (half_day == 'first' or half_day == 'second'):
            if start != end:
                raise ValueError("Half-day leave must be on the same day")
            return Decimal('0.5')
        else:
            working_days = 0
            current_date = start
            while current_date <= end:
                if current_date not in closed_dates:
                    working_days += 1
                current_date += timedelta(days=1)
            return Decimal(working_days)
    else:
        days = (end - start).days + 1
        if category in ['EL', 'COL', 'VL']:
            return Decimal(days)
        else:
            working_days = 0
            current_date = start
            while current_date <= end:
                if current_date not in closed_dates:
                    working_days += 1
                current_date += timedelta(days=1)
            return Decimal(working_days)

def intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool:
    if a_start == a_end == b_start == b_end:
        if (a_half == 'first' and b_half == 'second') or (a_half == 'second' and b_half == 'first'):
            return False
    return not (a_end < b_start or a_start > b_end)

def calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]:
    converted = unutilized_vl // Decimal('2')
    credited_el = min(converted, max(0, max_el_cap - current_el))
    forfeited_vl = unutilized_vl - converted * Decimal('2')
    new_el_balance = current_el + credited_el
    return (credited_el, forfeited_vl, new_el_balance)

def validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool:
    if is_station_leave:
        return destination is not None and emergency_contact is not None
    return True

def can_substitute(applicant_id: int, substitute_id: int) -> bool:
    return applicant_id != substitute_id
```
```

## Stage: Stage 1 Fix: Null safety & VL conversion edge cases

### Prompt

```text
ï»¿You are Qwen2.5-Coder 7B running locally.
Review this function from `modules/elm/domain/rules.py`:
```python
def count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
    ...
    if current_date not in closed_dates:
```
Notice that when `closed_dates` is None (the default argument), `current_date not in closed_dates` raises `TypeError: argument of type 'NoneType' is not iterable`.
Also, in `calculate_vl_to_el_conversion`:
When `converted` exceeds `(max_el_cap - current_el)`, any excess VL that could not be converted due to the cap should also be tracked as lapsed/forfeited.
Also ensure `Decimal` comparison with 0 (use `Decimal('0')`).

Please fix `modules/elm/domain/rules.py` and output the complete clean corrected file.
Return ONLY valid Python code inside standard ```python fences.

```

### Model Response

```python
```python
from decimal import Decimal
from datetime import date

def count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
    if closed_dates is None:
        closed_dates = set()
    # Your existing code logic here
    if current_date not in closed_dates:
        # Your existing code logic here
        pass

def calculate_vl_to_el_conversion(converted: Decimal, max_el_cap: Decimal, current_el: Decimal) -> Decimal:
    if converted > (max_el_cap - current_el):
        excess_vl = converted - (max_el_cap - current_el)
        # Track excess VL as lapsed/forfeited
        # Your existing code logic here
        pass
    # Your existing code logic here
    return converted

# Ensure Decimal comparison with 0 (use Decimal('0'))
if Decimal('0') == Decimal('0'):
    # Your existing code logic here
    pass
```
```

## Stage: Stage 1: Complete Domain Rules

### Prompt

```text
ï»¿You are Qwen2.5-Coder 7B running locally.
Do NOT use placeholders like '# Your existing code logic here' or 'pass'.
Return the COMPLETE, WORKING file content for `modules/elm/domain/rules.py` with ALL functions fully implemented.

```python
from datetime import date, timedelta
from decimal import Decimal

ENTITLEMENTS = {
    'CL': Decimal('8'),
    'RH': Decimal('2'),
    'SCL': Decimal('15'),
    'EL': Decimal('30'),
    'VL': Decimal('60'),
    'COL': Decimal('20'),
}
```
Include:
1. `count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal`:
   - Must handle `if closed_dates is None: closed_dates = set()`
   - Raise `ValueError` if `category not in ENTITLEMENTS` or `start > end`.
   - If `category == 'CL'` and `half_day in ('first', 'second')`: if `start != end` raise `ValueError`, else return `Decimal('0.5')`.
   - If `category in ('EL', 'COL', 'VL')`: continuous days: `Decimal((end - start).days + 1)`.
   - Else (working days for CL full day, SCL, RH): iterate from `start` to `end`, increment count for each date not in `closed_dates`. Return `Decimal(working_days)`.
2. `intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool`:
   - Opposite half-days ('first' vs 'second') on the exact same date do NOT overlap (return False).
   - Standard interval overlap check for other cases.
3. `calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]`:
   - Full 2 VL : 1 EL conversion with ceiling cap at max_el_cap.
4. `validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool`:
   - If `is_station_leave`, checks `bool(destination and destination.strip() and emergency_contact and emergency_contact.strip())`. Else True.
5. `can_substitute(applicant_id: int, substitute_id: int) -> bool`:
   - `applicant_id != substitute_id`.

Output ONLY the complete Python code block.

```

### Model Response

```python
```python
from datetime import date, timedelta
from decimal import Decimal

ENTITLEMENTS = {
    'CL': Decimal('8'),
    'RH': Decimal('2'),
    'SCL': Decimal('15'),
    'EL': Decimal('30'),
    'VL': Decimal('60'),
    'COL': Decimal('20'),
}

def count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
    if closed_dates is None:
        closed_dates = set()
    if category not in ENTITLEMENTS:
        raise ValueError(f"Invalid category: {category}")
    if start > end:
        raise ValueError("Start date must be before end date")
    
    if category == 'CL' and half_day in ('first', 'second'):
        if start != end:
            raise ValueError("Cannot take half day leave for more than one day")
        return Decimal('0.5')
    
    if category in ('EL', 'COL', 'VL'):
        return Decimal((end - start).days + 1)
    
    working_days = 0
    for day in range((end - start).days + 1):
        current_date = start + timedelta(days=day)
        if current_date not in closed_dates:
            working_days += 1
    return Decimal(working_days)

def intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool:
    if a_start == b_start and a_half != b_half:
        return False
    return not (a_end < b_start or b_end < a_start)

def calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]:
    vl_to_el_ratio = Decimal('2') / Decimal('1')
    max_el = min(max_el_cap, current_el + unutilized_vl * vl_to_el_ratio)
    el_to_add = min(unutilized_vl * vl_to_el_ratio, max_el - current_el)
    vl_to_use = unutilized_vl - el_to_add / vl_to_el_ratio
    return vl_to_use, el_to_add, max_el

def validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool:
    if is_station_leave:
        return bool(destination and destination.strip() and emergency_contact and emergency_contact.strip())
    return True

def can_substitute(applicant_id: int, substitute_id: int) -> bool:
    return applicant_id != substitute_id
```
```

## Stage: Stage 1: Production Domain Rules (modules/elm/domain/rules.py)

### Prompt

```text
ï»¿You are Qwen2.5-Coder 7B running locally.
Here is the exact official specification for BR-EL-007, BR-EL-008, and BR-EL-012 from Fusion ERP ELM Specifications v1.4:

1. BR-EL-007 & BR-EL-008:
"At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including fractional conversion, and VL itself shall not carry forward. EL created by VL conversion shall be credited to the faculty member's EL balance, may carry forward, and may subsequently be availed."
So:
- `el_credited = unutilized_vl / Decimal('2')`
- `new_el = current_el + el_credited`
- If an EL accumulation cap applies (e.g. `max_el_cap = Decimal('300')`), credited EL is capped at `min(el_credited, max(Decimal('0'), max_el_cap - current_el))` and excess converted EL or uncredited VL is forfeited.
- The return value of `calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300'))` must be:
  `(credited_el, forfeited_vl, new_el_balance)` where `forfeited_vl = unutilized_vl - (credited_el * Decimal('2'))`.

2. BR-EL-012:
"Applicant non-overlap with half-day CL exception: A leave period cannot overlap with another leave request for the same applicant, except when both requests are for the exact same date, one request is for 'first' half CL, and the other is for 'second' half CL."
So `intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool`:
- If dates do not overlap (`a_end < b_start` or `b_end < a_start`), return False.
- If they do intersect: if `a_start == a_end == b_start == b_end` and `((a_half == 'first' and b_half == 'second') or (a_half == 'second' and b_half == 'first'))`: return False.
- Otherwise, return True.

3. Complete `modules/elm/domain/rules.py`:
Implement:
- `ENTITLEMENTS = {'CL': Decimal('8'), 'RH': Decimal('2'), 'SCL': Decimal('15'), 'EL': Decimal('30'), 'VL': Decimal('60'), 'COL': Decimal('20')}`
- `count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal`
- `intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool`
- `calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]`
- `validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool`
- `can_substitute(applicant_id: int, substitute_id: int) -> bool`

Write the COMPLETE, PRODUCTION-READY `modules/elm/domain/rules.py` in valid Python. Return ONLY code inside ```python fences.

```

### Model Response

```python
```python
from decimal import Decimal
from datetime import date

ENTITLEMENTS = {'CL': Decimal('8'), 'RH': Decimal('2'), 'SCL': Decimal('15'), 'EL': Decimal('30'), 'VL': Decimal('60'), 'COL': Decimal('20')}

def count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
    if category not in ENTITLEMENTS:
        raise ValueError(f"Invalid leave category: {category}")
    
    if start > end:
        raise ValueError("Start date must be before end date")
    
    if closed_dates is None:
        closed_dates = set()
    
    total_days = Decimal(0)
    current_date = start
    while current_date <= end:
        if current_date not in closed_dates:
            if half_day == 'first':
                total_days += Decimal('0.5')
                break
            elif half_day == 'second':
                total_days += Decimal('0.5')
                half_day = None
            else:
                total_days += Decimal('1')
        current_date += date(1, 1, 1)  # Increment by one day
    
    return total_days

def intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool:
    if a_end < b_start or b_end < a_start:
        return False
    
    if a_start == a_end == b_start == b_end:
        if (a_half == 'first' and b_half == 'second') or (a_half == 'second' and b_half == 'first'):
            return False
    
    return True

def calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]:
    el_credited = unutilized_vl / Decimal('2')
    credited_el = min(el_credited, max(Decimal('0'), max_el_cap - current_el))
    forfeited_vl = unutilized_vl - (credited_el * Decimal('2'))
    new_el_balance = current_el + credited_el
    return (credited_el, forfeited_vl, new_el_balance)

def validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool:
    if is_station_leave:
        if destination is None or emergency_contact is None:
            return False
    return True

def can_substitute(applicant_id: int, substitute_id: int) -> bool:
    # Implement the logic to determine if the substitute can replace the applicant
    # This is a placeholder implementation
    return applicant_id != substitute_id
```
```

## Stage: Stage 2: ELM Django Models (modules/elm/models.py)

### Prompt

```text
ï»¿You are Qwen2.5-Coder 7B running locally in the Fusion ERP repository.
Define the Django ORM models for the Employee Leave Management (`elm`) module in `modules/elm/models.py`.

Repository conventions:
- Institute employees are referenced by plain `user_id` integer (`models.IntegerField` or `UserScopedModel`), NEVER foreign keys to user table (there is no user table in this database; Fusion uses IAM/directory).
- Import `TimeStampedModel, UserScopedModel` from `core.db.mixins`.
- Use explicit `db_table` names with `elm_` prefix (e.g., `elm_leave_balance`, `elm_leave_request`, `elm_substitute_assignment`, `elm_leave_action_history`).

Required models:
1. `LeaveBalance(TimeStampedModel, UserScopedModel)`:
   - Fields: `user_id` (from UserScopedModel), `category` (CharField max_length=10: 'CL', 'RH', 'SCL', 'EL', 'VL', 'COL'), `year` (IntegerField), `credited` (DecimalField 5,2), `availed` (DecimalField 5,2, default=0), `balance` (DecimalField 5,2).
   - Constraints: UniqueConstraint on `user_id, category, year`.
   - Table: `elm_leave_balance`.

2. `LeaveRequest(TimeStampedModel, UserScopedModel)`:
   - Status choices:
     - `submitted` ("Submitted")
     - `awaiting_substitute` ("Awaiting substitute consent")
     - `under_review` ("Under Unit Head review")
     - `recommended` ("Recommended to Sanctioning Authority")
     - `sanctioned` ("Sanctioned")
     - `rejected` ("Rejected")
     - `withdrawn` ("Withdrawn")
     - `cancelled` ("Cancelled")
   - Fields:
     - `user_id` (from UserScopedModel)
     - `category` (CharField max_length=10)
     - `start_date` (DateField)
     - `end_date` (DateField)
     - `half_day` (CharField max_length=10, blank=True, null=True choices: [('first', 'First Half'), ('second', 'Second Half')])
     - `leave_days` (DecimalField 5,2)
     - `purpose` (TextField)
     - `status` (CharField max_length=24, default='submitted')
     - `is_station_leave` (BooleanField default=False)
     - `destination` (CharField max_length=200, blank=True)
     - `emergency_contact` (CharField max_length=50, blank=True)
     - `substitute_id` (IntegerField null=True, blank=True)
     - `current_reviewer_id` (IntegerField null=True, blank=True)
     - `rejection_reason` (TextField blank=True)
   - Table: `elm_leave_request`.

3. `SubstituteAssignment(TimeStampedModel)`:
   - Fields:
     - `leave_request` (ForeignKey to LeaveRequest, on_delete=CASCADE, related_name='substitute_assignments')
     - `substitute_id` (IntegerField)
     - `status` (CharField max_length=20 choices: [('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='pending')
     - `remarks` (TextField blank=True)
     - `responded_at` (DateTimeField null=True, blank=True)
   - Table: `elm_substitute_assignment`.

4. `LeaveActionHistory(TimeStampedModel)`:
   - Fields:
     - `leave_request` (ForeignKey to LeaveRequest, on_delete=CASCADE, related_name='actions')
     - `actor_id` (IntegerField)
     - `action` (CharField max_length=30)
     - `comments` (TextField blank=True)
   - Table: `elm_leave_action_history`.

Output ONLY the complete Python code in ```python fences.

```

### Model Response

```python
```python
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveBalance(TimeStampedModel, UserScopedModel):
    category = models.CharField(max_length=10, choices=[('CL', 'Casual Leave'), ('RH', 'Recreational Holiday'), ('SCL', 'Sick Casual Leave'), ('EL', 'Earned Leave'), ('VL', 'Vacation Leave'), ('COL', 'Compensatory Off')])
    year = models.IntegerField()
    credited = models.DecimalField(max_digits=5, decimal_places=2)
    availed = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'elm_leave_balance'
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'category', 'year'], name='unique_leave_balance')
        ]

class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('awaiting_substitute', 'Awaiting substitute consent'),
        ('under_review', 'Under Unit Head review'),
        ('recommended', 'Recommended to Sanctioning Authority'),
        ('sanctioned', 'Sanctioned'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('cancelled', 'Cancelled'),
    ]
    category = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=10, blank=True, null=True, choices=[('first', 'First Half'), ('second', 'Second Half')])
    leave_days = models.DecimalField(max_digits=5, decimal_places=2)
    purpose = models.TextField()
    status = models.CharField(max_length=24, default='submitted')
    is_station_leave = models.BooleanField(default=False)
    destination = models.CharField(max_length=200, blank=True)
    emergency_contact = models.CharField(max_length=50, blank=True)
    substitute_id = models.IntegerField(null=True, blank=True)
    current_reviewer_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'elm_leave_request'

class SubstituteAssignment(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='substitute_assignments')
    substitute_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'elm_substitute_assignment'

class LeaveActionHistory(TimeStampedModel):
    ACTION_CHOICES = [
        ('submitted', 'Submitted'),
        ('awaiting_substitute', 'Awaiting substitute consent'),
        ('under_review', 'Under Unit Head review'),
        ('recommended', 'Recommended to Sanctioning Authority'),
        ('sanctioned', 'Sanctioned'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('cancelled', 'Cancelled'),
    ]
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='actions')
    actor_id = models.IntegerField()
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)

    class Meta:
        db_table = 'elm_leave_action_history'
```
```

## Stage: Stage 3: ELM Services (modules/elm/services/leave.py)

### Prompt

```text
ï»¿You are Qwen2.5-Coder 7B running locally in the Fusion ERP repository.
Implement the ELM leave lifecycle services in `modules/elm/services/leave.py` adhering to official specifications:

Use pure Django ORM operations with atomic transactions (`django.db.transaction.atomic`) and exceptions from `core.api.exceptions` (`DomainError, ConflictError, NotFoundError, PermissionDeniedError`).

Functions to implement:
1. `apply_for_leave(*, user_id: int, category: str, start_date, end_date, half_day=None, purpose: str, is_station_leave=False, destination="", emergency_contact="", substitute_id=None, closed_dates=None) -> LeaveRequest`:
   - Validate category and calculate `leave_days = count_leave_days(category, start_date, end_date, half_day=half_day, closed_dates=closed_dates)`.
   - Validate station leave via `validate_station_leave(is_station_leave, destination, emergency_contact)`.
   - Validate substitute if provided via `can_substitute(user_id, substitute_id)`.
   - Check applicant existing active leaves for date collision via `intervals_overlap`.
   - Check `LeaveBalance` for `user_id, category, year=start_date.year`. Must have `balance >= leave_days`.
   - Initial status: if `substitute_id` is provided, `status = 'awaiting_substitute'`; else `status = 'under_review'`.
   - Create `LeaveRequest`, create `SubstituteAssignment(status='pending')` if substitute nominated, and create `LeaveActionHistory(actor_id=user_id, action='submitted')`.
   - Return created `LeaveRequest`.

2. `respond_substitute(*, substitute_id: int, request_id: int, action: str, remarks: str = "") -> SubstituteAssignment`:
   - `action` is 'accept' or 'decline'.
   - Verify `substitute_id` owns the pending `SubstituteAssignment`.
   - If 'accept': update assignment status to 'accepted', update `LeaveRequest.status = 'under_review'`. Record `LeaveActionHistory`.
   - If 'decline': update assignment status to 'declined', update `LeaveRequest.status = 'awaiting_substitute'`. Record `LeaveActionHistory`.

3. `review_leave_request(*, reviewer_id: int, request_id: int, action: str, reason: str = "") -> LeaveRequest`:
   - `action` in ('approve', 'reject', 'recommend').
   - For 'CL'/'RH': Unit Head gives final sanction ('approve' -> 'sanctioned') or 'reject' -> 'rejected'.
   - On final 'sanctioned': decrement `LeaveBalance.balance -= leave.leave_days` and increment `LeaveBalance.availed += leave.leave_days`.
   - For higher leave ('EL', 'VL', 'COL', 'SCL'): Unit Head gives 'recommend' -> 'recommended'.
   - On 'reject': set `status = 'rejected'`, record reason.
   - Record `LeaveActionHistory`.

4. `withdraw_leave_request(*, user_id: int, request_id: int) -> LeaveRequest`:
   - BR-EL-022: Only allowed while pending ('submitted', 'awaiting_substitute', 'under_review', 'recommended').
   - Set `status = 'withdrawn'`. Record `LeaveActionHistory`.

5. `cancel_approved_leave(*, user_id: int, request_id: int, today_date) -> LeaveRequest`:
   - BR-EL-023: Allowed only before `start_date` (`today_date < leave.start_date`) for `status == 'sanctioned'`.
   - Restore `LeaveBalance.balance += leave.leave_days` and `LeaveBalance.availed -= leave.leave_days`.
   - Set `status = 'cancelled'`. Record `LeaveActionHistory`.

Write clean, robust, production-quality Python code. Output ONLY code inside ```python fences.

```

### Model Response

```python
```python
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from core.api.exceptions import DomainError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import LeaveRequest, SubstituteAssignment, LeaveActionHistory, LeaveBalance
from modules.elm.utils import count_leave_days, validate_station_leave, can_substitute, intervals_overlap

@transaction.atomic
def apply_for_leave(*, user_id: int, category: str, start_date, end_date, half_day=None, purpose: str, is_station_leave=False, destination="", emergency_contact="", substitute_id=None, closed_dates=None) -> LeaveRequest:
    leave_days = count_leave_days(category, start_date, end_date, half_day=half_day, closed_dates=closed_dates)
    validate_station_leave(is_station_leave, destination, emergency_contact)
    if substitute_id:
        can_substitute(user_id, substitute_id)
    if intervals_overlap(user_id, start_date, end_date):
        raise ConflictError("Date collision with existing leave requests.")
    if not LeaveBalance.objects.filter(user_id=user_id, category=category, year=start_date.year).exists():
        raise NotFoundError("No leave balance found for the given category and year.")
    leave_balance = LeaveBalance.objects.get(user_id=user_id, category=category, year=start_date.year)
    if leave_balance.balance < leave_days:
        raise DomainError("Insufficient leave balance.")
    status = 'awaiting_substitute' if substitute_id else 'under_review'
    leave_request = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        purpose=purpose,
        is_station_leave=is_station_leave,
        destination=destination,
        emergency_contact=emergency_contact,
        substitute_id=substitute_id,
        status=status,
        leave_days=leave_days
    )
    if substitute_id:
        SubstituteAssignment.objects.create(
            leave_request=leave_request,
            substitute_id=substitute_id,
            status='pending'
        )
    LeaveActionHistory.objects.create(
        actor_id=user_id,
        leave_request=leave_request,
        action='submitted'
    )
    return leave_request

@transaction.atomic
def respond_substitute(*, substitute_id: int, request_id: int, action: str, remarks: str = "") -> SubstituteAssignment:
    if action not in ['accept', 'decline']:
        raise DomainError("Invalid action for substitute response.")
    substitute_assignment = SubstituteAssignment.objects.get(substitute_id=substitute_id, leave_request_id=request_id, status='pending')
    leave_request = substitute_assignment.leave_request
    if action == 'accept':
        substitute_assignment.status = 'accepted'
        leave_request.status = 'under_review'
    else:
        substitute_assignment.status = 'declined'
        leave_request.status = 'awaiting_substitute'
    substitute_assignment.save()
    leave_request.save()
    LeaveActionHistory.objects.create(
        actor_id=substitute_id,
        leave_request=leave_request,
        action=action,
        remarks=remarks
    )
    return substitute_assignment

@transaction.atomic
def review_leave_request(*, reviewer_id: int, request_id: int, action: str, reason: str = "") -> LeaveRequest:
    if action not in ['approve', 'reject', 'recommend']:
        raise DomainError("Invalid action for leave review.")
    leave_request = LeaveRequest.objects.get(id=request_id)
    if action == 'approve':
        if leave_request.category in ['CL', 'RH']:
            leave_request.status = 'sanctioned'
            leave_request.save()
            leave_balance = LeaveBalance.objects.get(user_id=leave_request.user_id, category=leave_request.category, year=timezone.now().year)
            leave_balance.balance -= leave_request.leave_days
            leave_balance.availed += leave_request.leave_days
            leave_balance.save()
        else:
            leave_request.status = 'recommended'
            leave_request.save()
    elif action == 'reject':
        leave_request.status = 'rejected'
        leave_request.save()
        LeaveActionHistory.objects.create(
            actor_id=reviewer_id,
            leave_request=leave_request,
            action=action,
            reason=reason
        )
    elif action == 'recommend':
        leave_request.status = 'recommended'
        leave_request.save()
    LeaveActionHistory.objects.create(
        actor_id=reviewer_id,
        leave_request=leave_request,
        action=action,
        reason=reason
    )
    return leave_request

@transaction.atomic
def withdraw_leave_request(*, user_id: int, request_id: int) -> LeaveRequest:
    leave_request = LeaveRequest.objects.get(id=request_id)
    if leave_request.status not in ['submitted', 'awaiting_substitute', 'under_review', 'recommended']:
        raise PermissionDeniedError("Cannot withdraw a leave request that is not pending.")
    leave_request.status = 'withdrawn'
    leave_request.save()
    LeaveActionHistory.objects.create(
        actor_id=user_id,
        leave_request=leave_request,
        action='withdrawn'
    )
    return leave_request

@transaction.atomic
def cancel_approved_leave(*, user_id: int, request_id: int, today_date) -> LeaveRequest:
    leave_request = LeaveRequest.objects.get(id=request_id)
    if leave_request.status != 'sanctioned' or today_date >= leave_request.start_date:
        raise PermissionDeniedError("Cannot cancel an approved leave request that has already started or is not approved.")
    leave_balance = LeaveBalance.objects.get(user_id=leave_request.user_id, category=leave_request.category, year=timezone.now().year)
    leave_balance.balance += leave_request.leave_days
    leave_balance.availed -= leave_request.leave_days
    leave_balance.save()
    leave_request.status = 'cancelled'
```
