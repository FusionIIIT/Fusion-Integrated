# Blueprint: HR & Employee Information System (EIS) Module

**Module Code**: `hr_eis`  
**Base Path**: `/hr-eis`  
**Docs Folder**: `docs/09-hr_eis/`  
**Status**: Approved (Phase 2 Gate Cleared)  

---

## 1. Traceability Table

| Requirement / Spec ID | Specification Clause | Architectural Component | Implementation Target | Test Obligation / Test ID |
|---|---|---|---|---|
| **CFR-01** | Authenticated employee retrieves their own EIS profile via `/me` | DRF ViewSet Action | `EmployeeProfileViewSet.my_profile` | `FR-TC-01`, `FR-TC-02` |
| **CFR-02** | Unauthenticated requests to profiles and experiences are refused | DRF Permission Gate | `permissions.IsAuthenticated` | `FR-TC-03`, `FR-TC-04` |
| **CFR-03** | Profile data isolation: non-staff only sees self; staff sees all | QuerySet Filter | `EmployeeProfileViewSet.get_queryset` | `FR-TC-05`, `FR-TC-06` |
| **CFR-04** | Employee creates and lists their professional work experiences | ViewSet & Serializer | `WorkExperienceViewSet`, `WorkExperienceSerializer` | `FR-TC-07`, `FR-TC-08` |
| **CFR-05** | Profile string representation format `<username> (<pf_number>) - <designation>` | Model Method | `EmployeeProfile.__str__` | `FR-TC-13` |
| **CFR-06** | Work experience belongs to employee profile and supports deletion | Model Relationship & ViewSet | `WorkExperience.employee`, `perform_destroy` | `FR-TC-14` |
| **AFR-01** | `pf_number` uniqueness constraint across all employees | Database & Model Constraint | `EmployeeProfile.pf_number(unique=True)` | `FR-TC-09` |
| **AFR-02** | Chronological integrity: `end_date` must not precede `start_date` | Model & Serializer Validation | `WorkExperience.clean()`, `WorkExperienceSerializer.validate()` | `FR-TC-10`, `FR-TC-11` |
| **AFR-03** | Support ongoing professional experience with null `end_date` | Nullable Field Definition | `WorkExperience.end_date(null=True, blank=True)` | `FR-TC-12` |
| **UC-01** | Self-service profile viewing workflow | API & Frontend Page | `/api/v1/hr-eis/profiles/me/`, `ProfilePage.tsx` | `UC-TC-01`, `UC-TC-02`, `UC-TC-03` |
| **UC-02** | Add work experience workflow | API Modal & Serializer | `WorkExperienceModal.tsx`, `POST /experiences/` | `UC-TC-04`, `UC-TC-05`, `UC-TC-06` |
| **UC-03** | Staff employee directory exploration | Staff ViewSet QuerySet | `DirectoryPage.tsx`, `/api/v1/hr-eis/profiles/` | `UC-TC-07`, `UC-TC-08` |
| **UC-04** | Retrieve work experiences list | List ViewSet & Component | `WorkExperienceList.tsx`, `GET /experiences/` | `UC-TC-09`, `UC-TC-10` |
| **UC-05** | Delete work experience entry | Destroy Action | `DELETE /experiences/<id>/` | `UC-TC-11` |
| **BR-01** | Uniqueness of Provident Fund (PF) number | Model Integrity Rule | `EmployeeProfile.pf_number(unique=True)` | `BR-TC-01`, `BR-TC-02` |
| **BR-02** | Validation that end date is on or after start date | Domain Rule | `WorkExperience.clean()` | `BR-TC-03`, `BR-TC-04` |
| **BR-03** | Null end date indicates active/ongoing appointment | Business Rule | `WorkExperience.end_date` null acceptance | `BR-TC-05` |
| **BR-04** | Row-level data isolation between faculty profiles | RBAC & QuerySet Filter | `EmployeeProfileViewSet.get_queryset` | `BR-TC-06`, `BR-TC-07` |
| **BR-05** | Work experience scoped strictly to profile owner | QuerySet Ownership Scoping | `WorkExperienceViewSet.get_queryset` | `BR-TC-08` |
| **BR-06** | Mandatory session authentication for all EIS endpoints | Global / View Permission | `IsAuthenticated` | `BR-TC-09` |
| **BR-07** | Auto-link experience to authenticated user's profile | Mutation Hook | `WorkExperienceViewSet.perform_create` | `BR-TC-10` |
| **BR-08** | Designation restricted to recognized academic/staff tiers | Choices Tuple Validation | `EmployeeProfile.clean()` | `BR-TC-11` |
| **BR-09** | Department restricted to recognized institute faculties | Choices Tuple Validation | `EmployeeProfile.clean()` | `BR-TC-12` |
| **WF-01** | Profile View Lifecycle Workflow | REST Endpoint Flow | `GET /profiles/me/` | `WF-TC-01`, `WF-TC-02`, `WF-TC-03` |
| **WF-02** | Work Experience Creation Workflow | REST Endpoint Flow | `POST /experiences/` | `WF-TC-04`, `WF-TC-05`, `WF-TC-06` |
| **WF-03** | Profile Directory Listing Workflow | Staff / Self Scoped Flow | `GET /profiles/` | `WF-TC-07`, `WF-TC-08` |
| **WF-04** | Experience Removal Workflow | Delete Cascade / Action | `DELETE /experiences/<id>/` | `WF-TC-09` |
| **WF-05** | Identity Binding Workflow on Creation | Backend Hook Flow | `perform_create` auto-resolution | `WF-TC-10` |

---

## 2. Domain Model

```
+-------------------------------------------------------+
|                   EmployeeProfile                     |
+-------------------------------------------------------+
| id: BigAutoField [PK]                                 |
| user: OneToOneField(User, related_name='eis_profile') |
| pf_number: CharField(max_length=50, unique=True)      |
| designation: CharField(max_length=50, choices=...)    |
| department: CharField(max_length=50, choices=...)     |
| date_of_joining: DateField()                          |
| about_me: TextField(blank=True)                       |
+-------------------------------------------------------+
                           | 1
                           |
                           | 0..*
+-------------------------------------------------------+
|                    WorkExperience                     |
+-------------------------------------------------------+
| id: BigAutoField [PK]                                 |
| employee: ForeignKey(EmployeeProfile, cascade)        |
| organization: CharField(max_length=255)               |
| position: CharField(max_length=100)                   |
| start_date: DateField()                               |
| end_date: DateField(null=True, blank=True)            |
| description: TextField(blank=True)                    |
+-------------------------------------------------------+
```

### Constraints & Integrity
1. **Uniqueness**: `EmployeeProfile.pf_number` is unique and indexed.
2. **Date Ordering**: `WorkExperience.clean()` enforces `end_date >= start_date` if `end_date` is provided.
3. **Choice Sets**:
   - `DESIGNATION_CHOICES`: `PROFESSOR`, `ASSOC_PROF`, `ASST_PROF`, `STAFF`
   - `DEPARTMENT_CHOICES`: `CSE`, `ECE`, `ME`, `DESIGN`, `NS`

---

## 3. Permissions & Access Control

| Permission Code | Label | Scope | Usage |
|---|---|---|---|
| `hr_eis.profile.view_self` | View own employee profile | Faculty / Staff | Access personal profile at `/me/` and view personal experiences |
| `hr_eis.profile.manage_self` | Manage own experiences | Faculty / Staff | Create, update, and delete own work experiences |
| `hr_eis.profile.view_all` | View employee directory | HR Admin / Staff | List and search all employee profiles across institute |

---

## 4. Endpoints

| HTTP Method | Route | Permission | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/hr-eis/profiles/me/` | `IsAuthenticated` | Returns authenticated user's profile and nested experiences |
| `GET` | `/api/v1/hr-eis/profiles/` | `IsAuthenticated` | Returns self profile (faculty) or all profiles (staff) |
| `GET` | `/api/v1/hr-eis/profiles/<id>/` | `IsAuthenticated` | Returns specific profile if owner or staff |
| `GET` | `/api/v1/hr-eis/experiences/` | `IsAuthenticated` | Returns self experiences (faculty) or all experiences (staff) |
| `POST` | `/api/v1/hr-eis/experiences/` | `IsAuthenticated` | Creates a new work experience auto-linked to current user |
| `DELETE` | `/api/v1/hr-eis/experiences/<id>/` | `IsAuthenticated` | Deletes work experience if owned or staff |

---

## 5. Architectural Contracts & Isolation

- **Import Isolation**: Following `.importlinter`, `modules.hr_eis` communicates with external modules solely via contracts or IAM session attributes. Direct cross-module imports into other modules' internal models are strictly prohibited.
- **Frontend Independence**: The client module lives in `client/src/modules/hr_eis/` and communicates with the backend exclusively via standard HTTP REST API endpoints under `/api/v1/hr-eis/`.
- **Stateless Session Authentication**: Standard Fusion cookie sessions with CSRF tokens protect all state-changing endpoints.
