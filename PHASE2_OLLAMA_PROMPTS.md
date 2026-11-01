# Phase 2 — Ollama prompt log

Every prompt sent to the local model (`qwen2.5-coder:7b`, served by Ollama at
`http://localhost:11434`) while integrating and repairing `modules/leave/`, in
order, with the judge verdict and the action taken. New prompts are appended as
the work continues.

The loop run against the model is:

1. **Embed the real files** in the prompt — the local model has no filesystem
   access, so every fact it needs (source, spec text, error output) is pasted in.
2. **Generate** one small artefact at a time.
3. **Judge** the output automatically (`ops`-style checks, `ruff`, `manage.py
   check`, `tsc`) and by reading it.
4. **Feed the exact error back** and regenerate when the verdict is wrong.

A 7B model is reliable at short, fully-specified tasks and unreliable at
"edit this large file" tasks; the log records both, including where it had to be
corrected.

---
## P1 — wire `modules/leave` into Django (route every APIView)

### Prompt sent

```text
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4 + DRF).

The ELM leave module at modules/leave/ is NOT wired into Django. Make exactly 3 edits.

=== FILE 1: config/settings/base.py (relevant region, edit it) ===
# Each module is an independent Django app: own tables, migrations and contract.
PLATFORM_MODULES = [
    "modules.directory",         # who people are, projected from IAM
    "modules.accesscontrol",     # which modules a role may enter
]

# See docs/03-platform/module-authoring-guide.md to add one.
DOMAIN_MODULES = [
    "modules.placement",
]

INSTALLED_APPS = (DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
                  + PLATFORM_MODULES + DOMAIN_MODULES)

=== FILE 2: config/urls.py (full current contents) ===
"""Root URLs.

Every module mounts itself under /api/v1/<module>/. A module that is not in
INSTALLED_APPS contributes no URLs at all — that is what "independent" means
here: removing a module is deleting a directory and one settings line.
"""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

import core.api.schema  # noqa: F401  registers the auth schemes by import
from core.api.health import healthz, readyz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/v1/", include("fusion_auth.urls")),
    path("api/v1/directory/", include("modules.directory.api.urls")),
    path("api/v1/placement/", include("modules.placement.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]


=== FILE 3: modules/placement/api/urls.py (STYLE REFERENCE - copy this exact style) ===
from django.urls import path

from modules.placement.api import academics as a
from modules.placement.api import audit as au
from modules.placement.api import clearance as cl
from modules.placement.api import conduct as c
from modules.placement.api import documents as d
from modules.placement.api import exports as e
from modules.placement.api import registration as reg
from modules.placement.api import views as v

urlpatterns = [
    # postings
    path("postings", v.PostingListView.as_view(), name="placement-postings"),
    path("postings/<int:pk>", v.PostingDetailView.as_view(),
         name="placement-posting"),
    path("postings/<int:pk>/publish", v.PostingPublishView.as_view(),
         name="placement-posting-publish"),
    path("postings/<int:pk>/eligibility", v.PostingEligibilityView.as_view(),
         name="placement-posting-eligibility"),

    # applications
    path("applications", v.ApplicationListView.as_view(),
         name="placement-applications"),
    path("applications/apply", v.ApplyView.as_view(), name="placement-apply"),
    path("applications/<int:pk>/transition", v.ApplicationTransitionView.as_view(),
         name="placement-application-transition"),
    path("applications/<int:pk>/history", au.ApplicationHistoryView.as_view(),
         name="placement-application-history"),
    path("applications/bulk-transition",
         v.ApplicationBulkTransitionView.as_view(),
         name="placement-application-bulk-transition"),

    # documents
    path("documents", d.MyDocumentsView.as_view(), name="placement-documents"),
    path("documents/<int:pk>", d.MyDocumentDetailView.as_view(),
         name="placement-document"),
    path("documents/<int:pk>/download", d.DocumentDownloadView.as_view(),
         name="placement-document-download"),

    # profile
    path("profile/resume", v.MyResumeView.as_view(), name="placement-my-resume"),
    path("profiles/<int:user_id>", v.ProfileDetailView.as_view(),
         name="placement-profile"),

    # companies
    path("companies", v.CompanyListView.as_view(), name="placement-companies"),
    path("companies/<int:pk>/<str:action>", v.CompanyApprovalView.as_view(),
         name="placement-company-approval"),

    # interviews
    path("interviews/rounds", v.InterviewRoundListView.as_view(),
         name="placement-rounds"),
    path("interviews/rounds/<int:pk>/candidates", v.RoundCandidatesView.as_view(),
         name="placement-round-candidates"),
    path("interviews/rounds/<int:pk>/outcome", v.RoundOutcomeView.as_view(),
         name="placement-round-outcome"),

    # offers
    path("offers", v.OfferListView.as_view(), name="placement-offers"),
    path("offers/issue", v.OfferIssueView.as_view(), name="placement-offer-issue"),
    path("offers/<int:pk>/respond", v.OfferRespondView.as_view(),
         name="placement-offer-respond"),

    # announcements
    path("announcements", v.AnnouncementListView.as_view(),
         name="placement-announcements"),
    path("announcements/<int:pk>/withdraw", v.AnnouncementWithdrawView.as_view(),
         name="placement-announcement-withdraw"),

    # CPI directory — the whole cohort's declared standing, staff only
    path("students/cpi", a.AcademicDirectoryView.as_view(),
         name="placement-cpi-directory"),
    path("students/cpi/filters", a.AcademicFiltersView.as_view(),
         name="placement-cpi-filters"),

    # registration (rules 1, 20, 21)
    path("registrations", reg.MyRegistrationsView.as_view(),
         name="placement-registrations"),
    path("registrations/terms", reg.MyRegistrationTermsView.as_view(),
         name="placement-registration-terms"),
    path("registrations/opt-out", reg.MyOptOutView.as_view(),
         name="placement-registration-opt-out"),
    path("registrations/approve-late", reg.LateRegistrationView.as_view(),
         name="placement-registration-late"),
    path("registrations/re-register", reg.ReRegistrationView.as_view(),
         name="placement-reregistration"),

    # post-offer obligations (rules 22, 24)
    path("records", cl.MyRecordsView.as_view(), name="placement-my-records"),
    path("records/clearance", cl.MyClearanceView.as_view(),
         name="placement-my-clearance"),
    path("records/<int:pk>/offer-letter", cl.SubmitOfferLetterView.as_view(),
         name="placement-submit-offer-letter"),
    path("records/<int:pk>/not-joining", cl.NotJoiningView.as_view(),
         name="placement-not-joining"),
    path("records/outstanding", cl.OutstandingLettersView.as_view(),
         name="placement-outstanding-letters"),
    path("records/off-campus", cl.OffCampusRecordView.as_view(),
         name="placement-off-campus-record"),

    # conduct and sanctions (rules 18, 19, 21)
    path("conduct/incidents", c.IncidentListView.as_view(),
         name="placement-incidents"),
    path("conduct/incidents/<int:pk>/waive", c.IncidentWaiveView.as_view(),
         name="placement-incident-waive"),
    path("conduct/sanctions", c.SanctionView.as_view(),
         name="placement-sanction"),
    path("conduct/sanctions/lift", c.SanctionLiftView.as_view(),
         name="placement-sanction-lift"),

    path("conduct/mine", au.MyConductRecordView.as_view(),
         name="placement-my-conduct"),

    # exports — bulk personal data, staff only and throttled
    path("exports/applications.csv", e.ApplicationExportView.as_view(),
         name="placement-export-applications"),
    path("exports/placements.csv", e.PlacementRecordExportView.as_view(),
         name="placement-export-placements"),

    # seasons and statistics
    path("seasons", v.SeasonListView.as_view(), name="placement-seasons"),
    path("stats", v.StatsView.as_view(), name="placement-stats"),

    # recruiter portal
    path("recruiters/invite", v.RecruiterInviteView.as_view(),
         name="placement-recruiter-invite"),
    path("recruiters/accept", v.RecruiterAcceptView.as_view(),
         name="placement-recruiter-accept"),
    path("recruiters/login", v.RecruiterLoginView.as_view(),
         name="placement-recruiter-login"),
    path("recruiters/logout", v.RecruiterLogoutView.as_view(),
         name="placement-recruiter-logout"),
    path("recruiters/me", v.RecruiterMeView.as_view(),
         name="placement-recruiter-me"),
]


=== APIView classes found in modules/leave/api/views.py (method args shown) ===
MyRequestsView:
  get()
  post()
MyBalancesView:
  get()
RequestDetailView:
  get(pk)
WithdrawView:
  post(pk)
ReplacementSubstituteView:
  post(pk)
SubstitutionInboxView:
  get()
  post(pk)
TaskInboxView:
  get()
UnitHeadReviewView:
  post(pk)
EstablishmentRouteView:
  post(pk)
FinalDecisionView:
  post(pk)
ResumptionView:
  post(pk)
ResumptionReviewView:
  post(pk)
CancellationView:
  post(pk)
ExtensionView:
  post(pk)
ApprovedLeaveView:
  get()
AllRequestsView:
  get()
OfflineLeaveView:
  post()
PolicyView:
  get()
  post()
CalendarListView:
  get()
  post()
CalendarPublishView:
  post(pk)
VacationPeriodsView:
  post()
SlaSweepView:
  post()
YearEndView:
  post()
CalendarForYearView:

TASK:
1. settings: add "modules.leave" to DOMAIN_MODULES after "modules.placement".
2. CREATE modules/leave/api/urls.py routing EVERY class above:
   - start with `from django.urls import path` and `from modules.leave.api import views as v`
   - get-only classes without pk: path("<kebab-name>", v.NameView.as_view(), name="leave-<kebab>")
   - post/detail classes with pk: path("<kebab-name>/<int:pk>", v.NameView.as_view(), name="leave-<kebab>")
   - use REST-ish singular resource names like placement does (e.g. requests, requests/<int:pk>/withdraw,
     balances, inbox, resumption/<int:pk>, resumption/<int:pk>/review, policy, calendar, year-end, sla-sweep)
   - names must all start with "leave-"
3. config/urls.py: add path("api/v1/leave/", include("modules.leave.api.urls")), after the placement line.

Output ONLY:
(a) the complete contents of modules/leave/api/urls.py in one fenced code block labelled urls.py
(b) the one-line settings edit
(c) the one-line config/urls.py edit
No explanations.
```

### Verdict

**Result:** routed only 11 of 24 views; `calendar/publish` missing its `<int:pk>`.
**Action:** fed the missing-class list back (P1-fix).

## P1-fix — you missed 16 views

### Prompt sent

```text
Your modules/leave/api/urls.py is INCOMPLETE. It routes only 11 of 27 APIView classes.

Missing these classes (from modules/leave/api/views.py, method args shown):

class RequestDetailView(APIView):     def get(self, request, pk)
class ReplacementSubstituteView(APIView):  def post(self, request, pk)
class SubstitutionInboxView(APIView): def get(self, request)  def post(self, request, pk)
class TaskInboxView(APIView):         def get(self, request)
class UnitHeadReviewView(APIView):    def post(self, request, pk)
class EstablishmentRouteView(APIView): def post(self, request, pk)
class FinalDecisionView(APIView):     def post(self, request, pk)
class ResumptionReviewView(APIView):  def post(self, request, pk)
class CancellationView(APIView):      def post(self, request, pk)
class ExtensionView(APIView):         def post(self, request, pk)
class ApprovedLeaveView(APIView):     def get(self, request)
class AllRequestsView(APIView):       def get(self, request)
class OfflineLeaveView(APIView):      def post(self, request)
class VacationPeriodsView(APIView):   def post(self, request)
class CalendarForYearView(APIView):   def get(self, request)  # takes ?year= query param, no pk

Also your CalendarPublishView route is wrong: it is defined as
class CalendarPublishView(APIView):  def post(self, request, pk)
so it MUST be path("calendar/publish/<int:pk>", ...) not path("calendar/publish", ...).

Here is your previous answer:
```python
# urls.py
from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("requests", v.MyRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(), name="leave-withdraw"),
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),
    path("inbox", v.SubstitutionInboxView.as_view(), name="leave-inbox"),
    path("resumption/<int:pk>", v.ResumptionView.as_view(), name="leave-resumption"),
    path("resumption/<int:pk>/review", v.ResumptionReviewView.as_view(), name="leave-resumption-review"),
    path("policy", v.PolicyView.as_view(), name="leave-policy"),
    path("calendar", v.CalendarListView.as_view(), name="leave-calendar"),
    path("calendar/publish", v.CalendarPublishView.as_view(), name="leave-calendar-publish"),
    path("year-end", v.YearEndView.as_view(), name="leave-year-end"),
    path("sla-sweep", v.SlaSweepView.as_view(), name="leave-sla-sweep"),
]
```

```python
# settings/base.py
DOMAIN_MODULES = [
    "modules.placement",
    "modules.leave",
]
```

```python
# config/urls.py
path("api/v1/leave/", include("modules.leave.api.urls")),
```


Rules: no view may be missing; every path gets a name starting with "leave-";
classes with (self, request, pk) get "/<int:pk>"; REST-ish kebab resource names;
SubstitutionInboxView needs TWO routes (GET list + POST action), decide a sensible
POST action path like substitutions/respond with <int:pk>.

Reply with ONLY the complete corrected modules/leave/api/urls.py in one fenced code block.
```

### Verdict

**Result:** 20 routes, but **invented** `SubstitutionRespondView` (does not exist) and dropped
`MyBalancesView`, `PolicyView`, `YearEndView`, `TaskInboxView`; routed `ApprovedLeaveView` with a
`<int:pk>` it does not accept.
**Action:** wrote an automated judge (`.ollama/judge_urls.py`) that diffs the generated urlconf
against the real `views.py`, then fed its exact errors back (P1-fix2).

## P1-fix2 — automated-check errors

### Prompt sent

```text
Your modules/leave/api/urls.py failed an automated check with these errors:

INVENTED view: SubstitutionRespondView does not exist in views.py
MISSING view: MyBalancesView is never routed
MISSING view: PolicyView is never routed
MISSING view: ReplacementSubstituteView is never routed
MISSING view: TaskInboxView is never routed
MISSING view: YearEndView is never routed
PK EXTRA: ApprovedLeaveView takes no pk but path "requests/<int:pk>/approved" has <int:pk>

Ground truth extracted from modules/leave/api/views.py:
- class MyBalancesView: get(request)                      -> GET /balances, name leave-balances
- class PolicyView: get(request), post(request)           -> GET+POST /policy, name leave-policy
- class TaskInboxView: get(request)                       -> GET /inbox, name leave-task-inbox
- class YearEndView: post(request)                        -> POST /year-end, name leave-year-end
- class ReplacementSubstituteView: post(request, pk)      -> POST /requests/<int:pk>/replacement, name leave-replacement
- class ApprovedLeaveView: get(request) NO pk             -> GET /approved-leaves, name leave-approved-leaves
- SubstitutionInboxView: get(request) + post(request, pk) -> GET /substitutions + POST /substitutions/<int:pk>/respond
  (SubstitutionRespondView does NOT exist - use SubstitutionInboxView for both routes)

Your current version:
```python
# modules/leave/api/urls.py
from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("requests", v.MyRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(), name="leave-withdraw"),
    path("requests/<int:pk>/details", v.RequestDetailView.as_view(), name="leave-request-detail"),
    path("requests/<int:pk>/substitute", v.SubstitutionInboxView.as_view(), name="leave-substitution-inbox"),
    path("requests/<int:pk>/substitute/respond", v.SubstitutionRespondView.as_view(), name="leave-substitution-respond"),
    path("requests/<int:pk>/resumption", v.ResumptionView.as_view(), name="leave-resumption"),
    path("requests/<int:pk>/resumption/review", v.ResumptionReviewView.as_view(), name="leave-resumption-review"),
    path("requests/<int:pk>/unit-head-review", v.UnitHeadReviewView.as_view(), name="leave-unit-head-review"),
    path("requests/<int:pk>/establishment-route", v.EstablishmentRouteView.as_view(), name="leave-establishment-route"),
    path("requests/<int:pk>/final-decision", v.FinalDecisionView.as_view(), name="leave-final-decision"),
    path("requests/<int:pk>/cancellation", v.CancellationView.as_view(), name="leave-cancellation"),
    path("requests/<int:pk>/extension", v.ExtensionView.as_view(), name="leave-extension"),
    path("requests/<int:pk>/approved", v.ApprovedLeaveView.as_view(), name="leave-approved"),
    path("requests/all", v.AllRequestsView.as_view(), name="leave-all-requests"),
    path("offline-leave", v.OfflineLeaveView.as_view(), name="leave-offline-leave"),
    path("vacation-periods", v.VacationPeriodsView.as_view(), name="leave-vacation-periods"),
    path("calendar", v.CalendarListView.as_view(), name="leave-calendar"),
    path("calendar/publish/<int:pk>", v.CalendarPublishView.as_view(), name="leave-calendar-publish"),
    path("calendar/year/<int:year>", v.CalendarForYearView.as_view(), name="leave-calendar-year"),
    path("sla-sweep", v.SlaSweepView.as_view(), name="leave-sla-sweep"),
]
```


Return ONLY the full corrected modules/leave/api/urls.py, one fenced code block.
Every one of these 24 classes must appear: MyRequestsView, MyBalancesView,
RequestDetailView, WithdrawView, ReplacementSubstituteView, SubstitutionInboxView,
TaskInboxView, UnitHeadReviewView, EstablishmentRouteView, FinalDecisionView,
ResumptionView, ResumptionReviewView, CancellationView, ExtensionView,
ApprovedLeaveView, AllRequestsView, OfflineLeaveView, PolicyView, CalendarListView,
CalendarPublishView, VacationPeriodsView, SlaSweepView, YearEndView, CalendarForYearView.
```

### Verdict

**Result:** 24/24 views routed; one `PK EXTRA` on `ApprovedLeaveView` remained.
**Action:** one surgical removal round (P1-fix3).

## P1-fix3 — delete the one bad line

### Prompt sent

```text
Your modules/leave/api/urls.py has exactly ONE remaining error:

PK EXTRA: ApprovedLeaveView takes no pk but path "requests/<int:pk>/approved" has <int:pk>

class ApprovedLeaveView has only: def get(self, request)  -- no pk parameter.
The route must not contain <int:pk>.

Current file:
```python
# modules/leave/api/urls.py
from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("requests", v.MyRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(), name="leave-withdraw"),
    path("requests/<int:pk>/details", v.RequestDetailView.as_view(), name="leave-request-detail"),
    path("requests/<int:pk>/substitute", v.SubstitutionInboxView.as_view(), name="leave-substitution-inbox"),
    path("requests/<int:pk>/substitute/respond", v.SubstitutionInboxView.as_view(), name="leave-substitution-respond"),
    path("requests/<int:pk>/resumption", v.ResumptionView.as_view(), name="leave-resumption"),
    path("requests/<int:pk>/resumption/review", v.ResumptionReviewView.as_view(), name="leave-resumption-review"),
    path("requests/<int:pk>/unit-head-review", v.UnitHeadReviewView.as_view(), name="leave-unit-head-review"),
    path("requests/<int:pk>/establishment-route", v.EstablishmentRouteView.as_view(), name="leave-establishment-route"),
    path("requests/<int:pk>/final-decision", v.FinalDecisionView.as_view(), name="leave-final-decision"),
    path("requests/<int:pk>/cancellation", v.CancellationView.as_view(), name="leave-cancellation"),
    path("requests/<int:pk>/extension", v.ExtensionView.as_view(), name="leave-extension"),
    path("requests/<int:pk>/approved", v.ApprovedLeaveView.as_view(), name="leave-approved"),
    path("requests/all", v.AllRequestsView.as_view(), name="leave-all-requests"),
    path("offline-leave", v.OfflineLeaveView.as_view(), name="leave-offline-leave"),
    path("vacation-periods", v.VacationPeriodsView.as_view(), name="leave-vacation-periods"),
    path("calendar", v.CalendarListView.as_view(), name="leave-calendar"),
    path("calendar/publish/<int:pk>", v.CalendarPublishView.as_view(), name="leave-calendar-publish"),
    path("calendar/year/<int:year>", v.CalendarForYearView.as_view(), name="leave-calendar-year"),
    path("sla-sweep", v.SlaSweepView.as_view(), name="leave-sla-sweep"),
    path("policy", v.PolicyView.as_view(), name="leave-policy"),
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),
    path("inbox", v.TaskInboxView.as_view(), name="leave-task-inbox"),
    path("year-end", v.YearEndView.as_view(), name="leave-year-end"),
    path("replacement/<int:pk>", v.ReplacementSubstituteView.as_view(), name="leave-replacement"),
    path("approved-leaves", v.ApprovedLeaveView.as_view(), name="leave-approved-leaves"),
]
```


Return ONLY the full corrected modules/leave/api/urls.py, one fenced code block,
changing nothing else.
```

### Verdict

**Result:** the model **added** the correct `approved-leaves` route but did not remove the bad
`requests/<int:pk>/approved` one.
**Action:** retry (P1-fix4).

## P1-fix4 — regenerate with the file removed (FAILED)

### Prompt sent

```text
Delete exactly this one line from your urlpatterns list:

    path("requests/<int:pk>/approved", v.ApprovedLeaveView.as_view(), name="leave-approved"),

Reason: ApprovedLeaveView.get(self, request) has no pk, so that route crashes.
The line "path("approved-leaves", v.ApprovedLeaveView.as_view(), name="leave-approved-leaves")," already covers it.

Output the ENTIRE corrected modules/leave/api/urls.py in one fenced code block. Change nothing else. No explanation.
```

### Verdict

**Result:** collapsed — 157 tokens, invented `ApproveLeaveView`, `RejectLeaveView`,
`RequestDeleteView`, `RequestEditView`; only 2/24 routed. Cause: the prompt contained no file
contents, so the model hallucinated from nothing.
**Lesson:** never ask a small model to edit a file that is not in the prompt.
**Action:** retried with the full file embedded (P1-fix5).

## P1-fix5 — full file embedded, remove one line

### Prompt sent

```text
Here is modules/leave/api/urls.py:

```python
# modules/leave/api/urls.py
from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("requests", v.MyRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(), name="leave-withdraw"),
    path("requests/<int:pk>/details", v.RequestDetailView.as_view(), name="leave-request-detail"),
    path("requests/<int:pk>/substitute", v.SubstitutionInboxView.as_view(), name="leave-substitution-inbox"),
    path("requests/<int:pk>/substitute/respond", v.SubstitutionInboxView.as_view(), name="leave-substitution-respond"),
    path("requests/<int:pk>/resumption", v.ResumptionView.as_view(), name="leave-resumption"),
    path("requests/<int:pk>/resumption/review", v.ResumptionReviewView.as_view(), name="leave-resumption-review"),
    path("requests/<int:pk>/unit-head-review", v.UnitHeadReviewView.as_view(), name="leave-unit-head-review"),
    path("requests/<int:pk>/establishment-route", v.EstablishmentRouteView.as_view(), name="leave-establishment-route"),
    path("requests/<int:pk>/final-decision", v.FinalDecisionView.as_view(), name="leave-final-decision"),
    path("requests/<int:pk>/cancellation", v.CancellationView.as_view(), name="leave-cancellation"),
    path("requests/<int:pk>/extension", v.ExtensionView.as_view(), name="leave-extension"),
    path("requests/<int:pk>/approved", v.ApprovedLeaveView.as_view(), name="leave-approved"),
    path("requests/all", v.AllRequestsView.as_view(), name="leave-all-requests"),
    path("offline-leave", v.OfflineLeaveView.as_view(), name="leave-offline-leave"),
    path("vacation-periods", v.VacationPeriodsView.as_view(), name="leave-vacation-periods"),
    path("calendar", v.CalendarListView.as_view(), name="leave-calendar"),
    path("calendar/publish/<int:pk>", v.CalendarPublishView.as_view(), name="leave-calendar-publish"),
    path("calendar/year/<int:year>", v.CalendarForYearView.as_view(), name="leave-calendar-year"),
    path("sla-sweep", v.SlaSweepView.as_view(), name="leave-sla-sweep"),
    path("policy", v.PolicyView.as_view(), name="leave-policy"),
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),
    path("inbox", v.TaskInboxView.as_view(), name="leave-task-inbox"),
    path("year-end", v.YearEndView.as_view(), name="leave-year-end"),
    path("replacement/<int:pk>", v.ReplacementSubstituteView.as_view(), name="leave-replacement"),
    path("approved-leaves", v.ApprovedLeaveView.as_view(), name="leave-approved-leaves"),
]
```


One line in it is invalid:
    path("requests/<int:pk>/approved", v.ApprovedLeaveView.as_view(), name="leave-approved"),
because ApprovedLeaveView.get(self, request) accepts no pk. The route
path("approved-leaves", v.ApprovedLeaveView.as_view(), name="leave-approved-leaves")
already serves that view.

Produce the same file with ONLY that invalid line removed from urlpatterns.
Output the entire file in one fenced code block. Do not add, rename, or reword anything.
```

### Verdict

**Result:** reproduced the same bad line unchanged.
**Action:** switched tactics — gave the model the complete **validated route table** and asked for a
faithful transcription (P1-regen).

## P1-regen — transcribe the validated route table

### Prompt sent

```text
Write the file modules/leave/api/urls.py for a Django REST Framework app.
Use exactly this contract - every line is already verified, transcribe it faithfully:

from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("requests", v.MyRequestsView.as_view(), name="leave-requests"),
    path("requests/all", v.AllRequestsView.as_view(), name="leave-all-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="leave-request"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(), name="leave-withdraw"),
    path("requests/<int:pk>/replacement", v.ReplacementSubstituteView.as_view(), name="leave-replacement"),
    path("requests/<int:pk>/review", v.UnitHeadReviewView.as_view(), name="leave-unit-head-review"),
    path("requests/<int:pk>/route", v.EstablishmentRouteView.as_view(), name="leave-establishment-route"),
    path("requests/<int:pk>/decide", v.FinalDecisionView.as_view(), name="leave-final-decision"),
    path("requests/<int:pk>/cancellation", v.CancellationView.as_view(), name="leave-cancellation"),
    path("requests/<int:pk>/extension", v.ExtensionView.as_view(), name="leave-extension"),
    path("requests/<int:pk>/resumption", v.ResumptionView.as_view(), name="leave-resumption"),
    path("requests/<int:pk>/resumption/review", v.ResumptionReviewView.as_view(), name="leave-resumption-review"),
    path("substitutions", v.SubstitutionInboxView.as_view(), name="leave-substitutions"),
    path("substitutions/<int:pk>/respond", v.SubstitutionInboxView.as_view(), name="leave-substitution-respond"),
    path("approved-leaves", v.ApprovedLeaveView.as_view(), name="leave-approved-leaves"),
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),
    path("inbox", v.TaskInboxView.as_view(), name="leave-inbox"),
    path("offline-leave", v.OfflineLeaveView.as_view(), name="leave-offline-leave"),
    path("policy", v.PolicyView.as_view(), name="leave-policy"),
    path("calendar", v.CalendarListView.as_view(), name="leave-calendar"),
    path("calendar/publish/<int:pk>", v.CalendarPublishView.as_view(), name="leave-calendar-publish"),
    path("calendar/year/<int:year>", v.CalendarForYearView.as_view(), name="leave-calendar-year"),
    path("vacation-periods", v.VacationPeriodsView.as_view(), name="leave-vacation-periods"),
    path("sla-sweep", v.SlaSweepView.as_view(), name="leave-sla-sweep"),
    path("year-end", v.YearEndView.as_view(), name="leave-year-end"),
]

Reproduce this file EXACTLY, character for character, in one fenced code block. No changes, no explanation.
```

### Verdict

**Result:** 24/24 views routed, correct names, correct pk usage. **PASS** (after one judge bug
was fixed: a class with a no-pk list route plus a pk action route legitimately has both shapes).
**Action:** wrote the file, added `modules.leave` to `DOMAIN_MODULES`, mounted `api/v1/leave/`.

## P2b — add the missing domain `ValidationError` to the shared error module

### Prompt sent

```text
This is the SHARED platform error module core/api/exceptions.py:

"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)


The leave module (modules/leave/services/*.py, 4 files) does:
    from core.api.exceptions import ConflictError, NotFoundError, ValidationError
and raises ValidationError("...", code="...") for business-rule violations
(e.g. an extension requested on leave that is not ongoing).

There is NO ValidationError in this module, so the import crashes:
    ImportError: cannot import name 'ValidationError' from 'core.api.exceptions'

Add a ValidationError class to core/api/exceptions.py that:
- subclasses DomainError (so the existing exception_handler maps it automatically)
- has code = "validation_error"  (matching the code the handler already emits for DRF validation errors, line ~101)
- has status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
- has message = "The submitted data was not valid."
- has a short docstring explaining it is a well-formed request that violates a
  business rule (distinct from BadRequestError's malformed request and ConflictError's
  wrong-state 409)
Place it directly after the BadRequestError class, before NotFoundError.

Output ONLY the COMPLETE modified core/api/exceptions.py in one fenced code block.
Change nothing else in the file.
```

### Verdict

**Result:** added `class ValidationError(DomainError)` with `code="validation_error"`, 422,
placed after `BadRequestError`. Diff verified to contain **only** that addition. **PASS**
(`core/api/exceptions.py`).

## P3 — audit `domain/categories.py` against BR-EL-007/011/012

### Prompt sent

```text
The Django system check fails on this file modules/leave/models.py with 6 errors:

  leave.LeaveBalance.category:  (fields.E005) 'choices' must be a mapping of actual
      values to human readable names or an iterable containing (actual value, human
      readable name) tuples.
  leave.LeaveRequest.category:  (fields.E005) same
  leave.LeaveTransaction.category: (fields.E005) same
  leave.LeaveRequest: (models.E012) 'indexes' refers to the nonexistent field 'created_at'
  leave.LeaveRequest: (models.E012) 'indexes' refers to the nonexistent field 'created_at'
  leave.LeaveRequest: (models.E015) 'ordering' refers to the nonexistent field 'created_at'

Root causes:
1. `choices=cat.CATEGORIES` is wrong because modules/leave/domain/categories.py defines
   CATEGORIES as a tuple of bare strings: ("cl","rh","scl","el","col","vl").
   That same module also defines LABELS = {"cl": "Casual Leave", "rh": "Restricted Holiday",
   "scl": "Special Casual Leave", "el": "Earned Leave", "col": "Commuted Leave",
   "vl": "Vacation Leave"}.
2. core/db/mixins.py defines two SEPARATE abstract models:
     class TimeStampedModel(models.Model): created_at, updated_at
     class UserScopedModel(models.Model): user_id
   class LeaveRequest(UserScopedModel) therefore has NO created_at, yet its Meta
   ordering and indexes use "created_at".

Fix ONLY these, in this file:
A) Add near the top, after the KIND_CHOICES definition:
       CATEGORY_CHOICES = [(code, cat.LABELS[code]) for code in cat.CATEGORIES]
   and replace ALL THREE occurrences of `choices=cat.CATEGORIES` with
   `choices=CATEGORY_CHOICES`.
B) Change the LeaveRequest class declaration from
       class LeaveRequest(UserScopedModel):
   to
       class LeaveRequest(UserScopedModel, TimeStampedModel):
   so it gets created_at. TimeStampedModel is already imported at the top.
   Do NOT change any other model's base classes.

Here is the complete current file:

"""Employee Leave Management tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database, and a cross-boundary FK would
make this module impossible to lift out later (ADR-0013). The applicant's
employee kind, department and name are read through `directory's` contracts.

No business logic and no `save()` override: `bulk_update` and `queryset.update()`
bypass both anyway, so the rules live in `domain/` and the writes in
`services/`.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain import categories as cat
from modules.leave.domain.state_machine import (
    DRAFT,
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
    KIND_RESUMPTION,
    STATES,
)

#: Status and kind choices are read off the state machine, so a state added
#: there cannot be missing here.
STATUS_CHOICES = [(s, s.replace("_", " ")) for s in sorted(STATES)]
KIND_CHOICES = [
    (KIND_NEW, "New leave"),
    (KIND_EXTENSION, "Extension of ongoing leave"),
    (KIND_CANCELLATION, "Cancellation of approved leave"),
    (KIND_RESUMPTION, "Resumption of duty"),
]

#: Decisions recorded against a request, at whatever stage made them.
DECISIONS = [
    ("approve", "Approve"),
    ("reject", "Reject"),
    ("recommended", "Recommended"),
    ("not_recommended", "Not recommended"),
    ("accept", "Substitute accepted"),
    ("decline", "Substitute declined"),
]


class LeavePolicy(TimeStampedModel):
    """The current configured leave-policy parameters (BR-EL-030).

    One row is current at a time; there is no draft/publish/effective-version
    lifecycle in this baseline, so validation simply reads the latest row.
    """

    label = models.CharField(max_length=60, default="Leave policy")
    year_label = models.CharField(max_length=9)          # "2026-27"
    starts_on = models.DateField()
    ends_on = models.DateField()

    # Annual entitlements, per eligible employee (BR-EL-002..009).
    cl_days = models.PositiveSmallIntegerField(default=8)
    rh_days = models.PositiveSmallIntegerField(default=2)
    scl_days = models.PositiveSmallIntegerField(default=15)
    el_days = models.PositiveSmallIntegerField(default=30)
    vl_days = models.PositiveSmallIntegerField(default=60)
    col_days = models.PositiveSmallIntegerField(default=20)

    #: Unused VL converts to EL at 2 VL : 1 EL, fractions included.
    vl_per_el = models.PositiveSmallIntegerField(default=2)

    #: The higher-sanction path, as designations (BR-EL-018/019).
    authority_path = models.JSONField(default=list, blank=True)
    establishment_designation = models.CharField(max_length=60, blank=True)
    establishment_step_enabled = models.BooleanField(default=False)

    #: SLA thresholds for actionable tasks (BR-EL-038).
    reminder_hours = models.PositiveSmallIntegerField(default=48)
    escalation_hours = models.PositiveSmallIntegerField(default=120)

    #: The year-end boundary EVT-01 fires on.
    year_end_on = models.DateField()

    class Meta:
        db_table = "leave_policy"
        ordering = ["-id"]
        verbose_name_plural = "leave policies"

    def __str__(self) -> str:
        return f"{self.label} ({self.year_label})"

    @classmethod
    def current(cls) -> LeavePolicy:
        """The configured values in force right now."""
        return cls.objects.order_by("-id").first()

    @property
    def hierarchy(self):
        from modules.leave.domain.routing import Hierarchy

        return Hierarchy(
            authority_path=tuple(self.authority_path or ()),
            establishment_designation=self.establishment_designation,
            establishment_step_enabled=self.establishment_step_enabled)

    def entitlement(self, code: str) -> int:
        return {
            cat.CL: self.cl_days, cat.RH: self.rh_days, cat.SCL: self.scl_days,
            cat.EL: self.el_days, cat.VL: self.vl_days, cat.COL: self.col_days,
        }.get(code, 0)


class OrganizationalUnit(TimeStampedModel):
    """A department, section or office and its head (ACT-03).

    Leave-owned configuration, because the Unit Head is who this module routes
    to — the IAM directory knows a person's department but not who heads it.
    """

    name = models.CharField(max_length=120, unique=True)
    head_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "leave_org_unit"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LeaveBalance(UserScopedModel):
    """One employee's account for one category in one leave year.

    `opening` is what carried forward, `credited` is what the year added
    (annual entitlement, or EL produced by VL conversion), `used` is what has
    been consumed. Every change writes a LeaveTransaction, so the account can
    always be explained rather than merely trusted.
    """

    year_label = models.CharField(max_length=9)
    category = models.CharField(max_length=8, choices=cat.CATEGORIES)
    opening = models.DecimalField(max_digits=6, decimal_places=2,
                                  default=Decimal("0"))
    credited = models.DecimalField(max_digits=6, decimal_places=2,
                                   default=Decimal("0"))
    used = models.DecimalField(max_digits=6, decimal_places=2,
                               default=Decimal("0"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year_label", "category"],
                                    name="leave_balance_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year_label"],
                         name="leave_balance_owner_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.category} {self.year_label}"

    @property
    def available(self) -> Decimal:
        return self.opening + self.credited - self.used


class LeaveRequest(UserScopedModel):
    """A submitted leave-related request.

    One table for four kinds of request — new leave, extension, cancellation,
    resumption — because they share one state machine and differ only in what a
    final decision does to the leave they point at. That is also what makes
    "the approved leave is not edited in place" structural: an extension is a
    separate row that carries the incremental period, and the original stays
    exactly as it was sanctioned.
    """

    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_NEW)
    category = models.CharField(max_length=8, choices=cat.CATEGORIES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=DRAFT)

    from_date = models.DateField()
    to_date = models.DateField()
    #: Set for a half-day CL (BR-EL-010).
    half = models.CharField(max_length=6, blank=True,
                            choices=[(h, h) for h in cat.HALVES])
    days = models.DecimalField(max_digits=6, decimal_places=2)

    purpose = models.TextField(max_length=1000)

    #: Station Leave details, captured inside the same application (BR-EL-013).
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=300, blank=True)

    #: The approved leave this request acts on.
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True,
                               blank=True, related_name="amendments")

    #: Routing, frozen at submission so a configuration change cannot move a
    #: request that is already halfway through the hierarchy.
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    final_authority = models.CharField(max_length=60, blank=True)
    establishment_first = models.BooleanField(default=False)
    self_sanction = models.BooleanField(default=False)
    #: The applicant's designations, as they were when the request was raised.
    #: Frozen because the Director-specific rule (BR-EL-020) is about who the
    #: applicant IS, and a later role change must not move a live request.
    applicant_roles = models.JSONField(default=list, blank=True)

    #: Responsibility coverage (BR-EL-014/015).
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_response = models.CharField(max_length=12, blank=True)
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    #: Offline-sanctioned leave recorded after the fact (EL-UC-016).
    is_offline = models.BooleanField(default=False)
    sanction_reference = models.CharField(max_length=120, blank=True)
    sanctioned_on = models.DateField(null=True, blank=True)
    offline_reason = models.CharField(max_length=300, blank=True)

    #: The final decision, once there is one.
    decision = models.CharField(max_length=20, blank=True, choices=DECISIONS)
    decision_remarks = models.CharField(max_length=300, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(to_date__gte=models.F("from_date")),
                                   name="leave_request_period_valid"),
            models.CheckConstraint(condition=Q(days__gte=0),
                                   name="leave_request_days_non_negative"),
            models.CheckConstraint(
                condition=Q(half="") | Q(half__in=list(cat.HALVES)),
                name="leave_request_half_valid"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status", "-created_at"],
                         name="leave_request_owner_idx"),
            models.Index(fields=["status", "category", "-created_at"],
                         name="leave_request_queue_idx"),
            models.Index(fields=["substitute_user_id", "status"],
                         name="leave_request_substitute_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.category} {self.from_date}..{self.to_date}"

    @property
    def is_pending(self) -> bool:
        from modules.leave.domain.state_machine import is_pending

        return is_pending(self.status)

    @property
    def interval(self) -> cat.Interval:
        return cat.Interval(self.from_date, self.to_date, self.half or None)


class LeaveApproval(TimeStampedModel):
    """Append-only record of every decision taken on a request.

    Never updated, never deleted: the audit trail is the only place the
    recommendation history survives, and "Not Recommended is not a final
    rejection" is only defensible if the recommendation is still on file.
    """

    STAGES = [
        ("employee", "Employee"),
        ("substitute", "Substitute consent"),
        ("unit_head", "Unit Head"),
        ("establishment", "Establishment"),
        ("final", "Final sanctioning authority"),
        ("self_sanction", "Director self-sanction"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="approvals")
    stage = models.CharField(max_length=16, choices=STAGES)
    decision = models.CharField(max_length=20, choices=DECISIONS)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_approval"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["request", "created_at"],
                         name="leave_approval_request_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.stage}: {self.decision}"


class LeaveTask(TimeStampedModel):
    """An actionable workflow task, and the SLA clock that runs against it.

    Created when a request reaches a stage that needs a person, and superseded
    the moment it moves on — so "no escalation if the task is no longer pending"
    is a query against this table rather than a promise (BR-EL-032/033).
    """

    STATUS = [("pending", "Pending"), ("completed", "Completed"),
              ("superseded", "Superseded"), ("cancelled", "Cancelled")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="tasks")
    stage = models.CharField(max_length=16, choices=LeaveApproval.STAGES)
    assignee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")

    assigned_at = models.DateTimeField(auto_now_add=True)
    actioned_at = models.DateTimeField(null=True, blank=True)
    #: SLA deadlines, stamped from the policy at assignment time.
    reminder_due_at = models.DateTimeField(null=True, blank=True)
    escalation_due_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_task"
        ordering = ["-created_at"]
        indexes = [
            # The reminder sweep's query: pending tasks, oldest deadline first.
            models.Index(fields=["status", "reminder_due_at"],
                         name="leave_task_sla_idx"),
            models.Index(fields=["assignee_user_id", "status"],
                         name="leave_task_assignee_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.stage} -> {self.assignee_user_id} ({self.status})"


class LeaveTransaction(TimeStampedModel):
    """The account ledger. Every balance change is a row here.

    A balance that cannot explain itself is a balance nobody can audit, which
    matters most at year end, when lapse, conversion and carry-forward all land
    on the same evening.
    """

    KINDS = [
        ("annual_credit", "Annual entitlement credited"),
        ("carry_forward", "Carried forward from the previous year"),
        ("approval", "Deducted for approved leave"),
        ("cancellation_reversal", "Restored by an approved cancellation"),
        ("extension_post", "Incremental period posted by an extension"),
        ("resumption_adjustment", "Adjustment after resumption review"),
        ("year_end_lapse", "Lapsed at the year-end boundary"),
        ("year_end_conversion", "Converted to another category"),
        ("offline_entry", "Offline-sanctioned leave recorded"),
    ]

    user_id = models.IntegerField(db_index=True)
    year_label = models.CharField(max_length=9)
    category = models.CharField(max_length=8, choices=cat.CATEGORIES)
    kind = models.CharField(max_length=24, choices=KINDS)
    #: Signed: positive credits the account, negative consumes it.
    days = models.DecimalField(max_digits=6, decimal_places=2)
    request = models.ForeignKey(LeaveRequest, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="transactions")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "leave_transaction"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["user_id", "year_label", "category"],
                         name="leave_txn_account_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.days} {self.category}"


class LeaveCalendar(TimeStampedModel):
    """The holiday/RH calendar for a leave year (EL-UC-015).

    Until a replacement is PUBLISHED, the currently effective one governs date
    and RH validation (BR-EL-031) — so "effective" is a property of what is
    published, never of what is being drafted.
    """

    year_label = models.CharField(max_length=9, unique=True)
    label = models.CharField(max_length=120, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_calendar"
        ordering = ["-year_label"]

    def __str__(self) -> str:
        return f"{self.year_label}{' (published)' if self.published_at else ' (draft)'}"


class CalendarEntry(TimeStampedModel):
    """One day in a calendar: a closed holiday, a Restricted Holiday, or a
    vacation period from the Academic Calendar (EXT-01)."""

    KINDS = [
        ("closed_holiday", "Closed holiday"),
        ("restricted_holiday", "Restricted holiday"),
        ("vacation", "Vacation period"),
    ]

    calendar = models.ForeignKey(LeaveCalendar, on_delete=models.CASCADE,
                                 related_name="entries")
    date = models.DateField()
    #: Inclusive; only used by a vacation period, which spans many days.
    ends_on = models.DateField(null=True, blank=True)
    kind = models.CharField(max_length=20, choices=KINDS)
    label = models.CharField(max_length=160, blank=True)

    class Meta:
        db_table = "leave_calendar_entry"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                    name="leave_calendar_entry_unique"),
        ]
        indexes = [
            models.Index(fields=["calendar", "kind", "date"],
                         name="leave_calendar_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.kind}"


class LeaveNotification(TimeStampedModel):
    """A notification this module decided to send.

    Written inside the same transaction as the decision that caused it, so a
    notification can never claim something that was rolled back. The delivery
    worker is not part of this change — see the module doc's list of gaps.
    """

    STATUS = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(db_index=True)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                null=True, blank=True, related_name="notifications")

    class Meta:
        db_table = "leave_notification"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id}"


Output ONLY the complete corrected modules/leave/models.py in one fenced code block.
Make no other changes.
```

### Verdict

**Result:** this large prompt (whole file embedded) **timed out** — no output.
**Lesson:** the full 462-line file plus instruction exceeded the practical budget for the 7B.
**Action:** split into small outputs (P3-first, then P3b).

## P3b — focused: the three lines to change

### Prompt sent

```text
Django model file modules/leave/models.py has these errors:
  fields.E005 on category fields: 'choices' must be an iterable of (value, label) tuples.
  models.E012/E015 on LeaveRequest: ordering/indexes refer to nonexistent field 'created_at'.

Context facts:
- modules/leave/domain/categories.py defines:
    CATEGORIES = ("cl", "rh", "scl", "el", "col", "vl")   # bare strings, NOT tuples
    LABELS = {"cl": "Casual Leave", "rh": "Restricted Holiday", "scl": "Special Casual Leave",
              "el": "Earned Leave", "col": "Commuted Leave", "vl": "Vacation Leave"}
- core/db/mixins.py defines two SEPARATE abstract models:
    class TimeStampedModel(models.Model): created_at, updated_at
    class UserScopedModel(models.Model): user_id
- models.py already imports TimeStampedModel at the top.
- models.py currently declares:  class LeaveRequest(UserScopedModel):
- Three fields use: choices=cat.CATEGORIES

Give me EXACTLY these three outputs and nothing else:

1) One line to add after the KIND_CHOICES block that builds a proper Django choices
   list from cat.CATEGORIES and cat.LABELS, named CATEGORY_CHOICES.

2) The exact new class declaration line for LeaveRequest that also gives it created_at.

3) A sed-style instruction list to replace the three `choices=cat.CATEGORIES` with
   the new CATEGORY_CHOICES name (just say: replace every occurrence of X with Y).

Output each as a short labelled snippet. No code blocks except plain lines.
```

### Verdict

**Result:** correct in intent but used unqualified names and a loop variable that shadowed the
`cat` module import: `[(cat, LABELS[cat]) for cat in CATEGORIES]`.
**Action:** judged wrong; corrected to
`CATEGORY_CHOICES = [(code, cat.LABELS[code]) for code in cat.CATEGORIES]` before applying.

## P3-first — verdict on each BR (round 1)

### Prompt sent

```text
You are auditing modules/leave/domain/categories.py against the official spec.
Each rule's authoritative statement is given. Find every place the code contradicts it,
and give the corrected line(s). Cite the rule number for each finding.

--- BR-EL-007 (VL-to-EL year-end conversion) ---
Spec: "At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including
fractional conversion, and VL itself shall not carry forward."
"Convert at 2:1 including fractions."
Code:
def year_end_action(code, available, *, vl_per_el=2):
    if available <= 0:
        return YearEndAction("none", available)
    c = category(code)
    if code == VL:
        return YearEndAction(CONVERT, available * Decimal(vl_per_el), target=EL)
    if c.carries_forward:
        return YearEndAction(CARRY_FORWARD, available)
    return YearEndAction(LAPSE, available)

--- BR-EL-011 (Continuous-day counting) ---
Spec: "For EL, COL, and VL, intervening weekends and closed holidays inside the continuous
approved interval count as leave days; this rule does not apply to CL, SCL, or RH."
(So for CL/SCL/RH the weekends must be REMOVED from the count. Both weekend days.)
Code:
def weekend_dates(start, end):
    """Saturday and Sunday inside the interval, inclusive."""
    out, d = set(), start
    while d <= end:
        if d.weekday() > 5:
            out.add(d)
        d = date.fromordinal(d.toordinal() + 1)
    return out
# used as: duty = span_days(start, end) - len(weekend_dates(start, end) | set(closed_dates))

--- BR-EL-012 (Applicant non-overlap with half-day CL exception) ---
Spec: "first-half and second-half CL on the same date are non-overlapping when they occupy
different halves."
Code:
    def overlaps(self, other):
        """BR-EL-012."""
        if self.end < other.start or other.end < self.start:
            return False
        same_day = (self.start == self.end == other.start == other.end)
        if same_day and self.half and other.half and self.half == other.half:
            return False
        return True

Python: date.weekday() returns 0=Monday .. 5=Saturday, 6=Sunday.

For EACH of the three functions output exactly:
  RULE: <BR number>
  VERDICT: correct | contradicts spec
  WRONG LINE: <verbatim if any>
  CORRECT LINE: <verbatim replacement>
  CONSEQUENCE: <one sentence, with a concrete example of the wrong number returned>

If a function is correct, say so. No other prose.
```

### Verdict

**Result:** found **1 of 3** — correctly flagged BR-EL-011 (`> 5` should be `>= 5`), but
declared BR-EL-007 and BR-EL-012 "correct" when both contradict the spec.
**Action:** two pointed counter-questions (P3-second).

## P3-second — counter-questions on the two misses

### Prompt sent

```text
Two of your verdicts were wrong. Answer these two questions precisely.

QUESTION 1 (BR-EL-007):
The spec says VL converts at "2 VL : 1 EL". That means 2 VL become 1 EL, so 10 unused VL
must become 5 EL.
The code computes:   available * Decimal(vl_per_el)   with vl_per_el=2
With available=10 that returns 20, but the spec requires 5.
a) VERDICT: what is wrong?
b) CORRECT LINE: give the exact corrected Python return line.
c) CONSEQUENCE: state what 10 VL wrongly produces and what it should produce.

QUESTION 2 (BR-EL-012):
Spec: "first-half and second-half CL on the same date are non-overlapping when they
occupy different halves." So this call MUST return False:
    Interval(date(2026,10,5), date(2026,10,5), "first").overlaps(
        Interval(date(2026,10,5), date(2026,10,5), "second"))
Walk through the code below with those exact values and state what it returns:
    def overlaps(self, other):
        if self.end < other.start or other.end < self.start:
            return False
        same_day = (self.start == self.end == other.start == other.end)
        if same_day and self.half and other.half and self.half == other.half:
            return False
        return True
a) What does it return for different halves ("first" vs "second")?
b) WRONG LINE: which operator in the `same_day` line is inverted?
c) CORRECT LINE: give the exact corrected line.
d) What is the requirement? That same halves overlap and different halves do not.

Output only answers labelled 1a,1b,1c and 2a,2b,2c,2d. No code blocks.
```

### Verdict

**Result:** BR-EL-007 now correct (diagnosed 10 VL → 20 instead of 5; gave a numerically
equivalent `/` line). BR-EL-012: correctly named the inverted `==`, but **edited the wrong line**
(`same_day`); the real inverted line is `self.half == other.half`.
**Action:** applied all three fixes with the `!=` correction made by the judge:
`weekend_dates` → `>= 5`, `overlaps` → `self.half != other.half`, `year_end_action` → `available /
Decimal(vl_per_el)`. Verified: 10 VL → 5 EL, different halves do not overlap, Sat+Sun both weekends.

## P3-tests — write `test_domain_rules.py`

### Prompt sent

```text
Write a pytest file modules/leave/tests/test_domain_rules.py for a pure-Python leave
domain module `modules.leave.domain.categories` (imported as `cat`).
No Django, no database. Use only datetime.date and decimal.Decimal.

The API:
  cat.weekend_dates(start: date, end: date) -> set[date]      # Saturdays AND Sundays, inclusive
  cat.Interval(start: date, end: date, half: str|None)        # half is "first" or "second"
      .overlaps(other: Interval) -> bool
  cat.year_end_action(code: str, available: Decimal, *, vl_per_el: int = 2) -> YearEndAction
      YearEndAction has fields: kind, amount, target
  cat.year_end_action returns kind "convert" with target "el" for code "vl" (cat.VL)
  codes: cat.CL="cl", cat.RH="rh", cat.SCL="scl", cat.EL="el", cat.COL="col", cat.VL="vl"

Write these tests exactly:

1. BR-EL-011 — weekend_dates returns BOTH Saturday and Sunday:
   - for 2026-10-09 (Fri) .. 2026-10-11 (Sun): 2026-10-10 (Sat) IS in the set and
     2026-10-11 (Sun) IS in the set.
   - a Monday..Friday range returns an empty set.
   - a single Saturday returns exactly that one date.

2. BR-EL-012 — half-day CL overlap on the same date:
   - two "first" halves on the same date OVERLAP (overlaps() is True).
   - "first" vs "second" on the same date do NOT overlap (False).
   - plain full-day intervals on overlapping date ranges overlap (True).
   - completely disjoint dates do not overlap (False).

3. BR-EL-007 — VL converts to EL at 2 VL : 1 EL:
   - year_end_action(cat.VL, Decimal(10), vl_per_el=2).amount == Decimal(5)
     and .target == cat.EL
   - Decimal(7) VL -> Decimal("3.5") EL (fractional conversion kept)
   - year_end_action(cat.EL, Decimal(4)).kind is a carry-forward kind (not "lapse")

Add a short module docstring citing BR-EL-007, BR-EL-011, BR-EL-012.
Output ONLY the complete file in one fenced code block. No prose.
```

### Verdict

**Result:** valid pytest file covering all three rules. **PASS** — 3 tests pass.
(Added the `tests/__init__.py` package marker and ran `pytest`.)
