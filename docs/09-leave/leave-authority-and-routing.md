---
owner: leave-lead
status: authoritative
last-reviewed: 2026-08-31
---

# Authority, Routing and Scope

BR-EL-016 to BR-EL-020. Who reviews a request, who finally grants it, and who may see it at all.

---

## Routing is configuration

`AuthorityRule` rows decide the path. Nothing in `domain/authority.py` names an office: the candidate
rules are supplied by the caller from the database, and the domain only decides which one applies and
what it implies. A reorganisation is therefore a row, not a deployment.

| Column | Meaning |
|---|---|
| `category` | The leave type this rule governs |
| `unit` | The department it applies to. **Empty matches any unit.** |
| `designation` | The applicant's designation. Empty matches any. |
| `applies_to_faculty` | `true`/`false` to narrow to one kind of employee, null for both |
| `establishment_step` | Whether the establishment section sits between recommendation and sanction |
| `sanctioning_designation` | Who finally decides. **Empty means the unit head is final.** |
| `self_sanction` | BR-EL-020. The holder sanctions their own leave — the Director's case. |
| `specificity` | Higher wins where several rows match |

### How a rule is chosen

The most specific match wins. Ties break on how much the rule actually constrains, so a rule naming a
unit *and* a designation beats one naming only the category:

```
(specificity, has unit, has designation, names an employee kind)
```

An explicit `specificity` on the row beats all of it — the escape hatch for a case the ordering does
not anticipate. If nothing matches, `NoAuthorityConfigured` is raised and the request is refused. It
does **not** fall back to a default approver: silently routing leave to whoever happens to be
convenient is worse than refusing to accept the application.

### The resulting path

| Configuration | Path |
|---|---|
| Unit head final (typical `CL`, `RH`) | applicant → *(substitute)* → unit head → **approved** |
| Higher sanction, no establishment step | applicant → *(substitute)* → unit head recommends → sanctioning authority |
| Higher sanction with establishment step | applicant → *(substitute)* → unit head recommends → establishment routes → sanctioning authority |
| Self-sanction | applicant → **self-sanction** |

A substitute is nominated only where one is required; the consent step is skipped otherwise.

---

## Two gates on every endpoint

1. **The module grant.** `HasModuleGrant("leave")` — is this module yours at all? This is also what
   drives the sidebar, so a role without the grant sees no leave link and can route to no leave page.
2. **The permission.** `HasPermission("leave.request.sanction")` and so on, one per action.

Both must pass. A view that declares nothing gets authentication and nothing else, so forgetting to
think about authorization fails closed.

### Permissions

| Code | Held by |
|---|---|
| `leave.request.create` / `.view_self` / `.withdraw` | every employee |
| `leave.substitute.respond` | every employee |
| `leave.request.review` | unit heads |
| `leave.request.route` | establishment |
| `leave.request.sanction` | sanctioning authorities |
| `leave.resumption.verify` | establishment |
| `leave.balance.view` | unit heads, establishment, administrators |
| `leave.policy.manage` / `.calendar.manage` / `.offline.record` | leave administrator |
| `leave.yearend.run` | the scheduled job, not a person |

---

## Scope is a queryset, never a check afterwards

`selectors/scoping.py` narrows before the row is fetched, so asking for somebody else's request returns
**404, not 403**. A refusal would confirm the request exists, which is an id-enumeration oracle.

| Who | Sees |
|---|---|
| An employee | their own rows |
| A unit head | their own unit, plus their own rows |
| Establishment, sanctioning authority, administrator | the institute |

**Holding `leave.balance.view` is deliberately not enough to see everything.** Every unit head holds it,
and reading it as institute-wide would let one department open another's leave records. The
institute-wide set is `route`, `sanction`, `resumption.verify` and `offline.record` — the roles that
genuinely act on requests from anywhere.

`review_queue(unit)` takes the unit as a **required** argument. An optional one defaults to "every unit"
the moment a caller forgets it, and a widened queue is the kind of mistake that reads as working
software.

## Nobody decides their own leave

A unit head is an employee too, and their own request lands in the queue they work from. Without a rule
they could approve it, and the trail would show an approval indistinguishable from any other.

`apply_event` refuses any decision where the actor is the applicant, whatever the role — review,
routing, sanction, resumption verification. It is enforced at the workflow choke point rather than in
each service, because a rule repeated in six places is a rule missing from the seventh.

Two exceptions, both deliberate:

- **The applicant acting on their own request** — withdrawing, renominating, reporting resumption. Those
  are `EMPLOYEE` actions on their own leave, which is the normal case.
- **Self-sanction (BR-EL-020)** — the Director's own leave has to go somewhere. It is reached only from
  `AWAITING_SELF_SANCTION`, a state the authority configuration put the request in, so it cannot be
  reached by accident from an ordinary route.

The queues exclude the viewer's own request as well. The service would refuse the decision anyway, but a
queue is a list of work somebody is expected to do, and offering a head their own leave with an Approve
button beside it is its own defect. `viewer_user_id` is a **required** argument for the same reason
`unit` is.

---

### Where the unit comes from

IAM's session carries no organisational unit, so the API resolves it from
`modules.directory.contracts.get_users` rather than off the credential. An unknown department yields an
empty unit, which matches nothing.

This also means the applicant and the unit on a submitted request are both taken from the credential
and the directory — never from the request body. A `user_id` in the body of an application is ignored;
there is an API test that pins exactly that.
