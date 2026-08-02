---
owner: frontend-lead
status: authoritative
last-reviewed: 2026-08-01
---

# State & Data Fetching

**There is no global store.** Nearly everything the old client kept in Redux is server state, and belongs in
TanStack Query.

---

## Where state lives

| Kind | Example | Home |
|---|---|---|
| Server data | postings, applications, the session | **TanStack Query** |
| URL state | filters, pagination cursor, active tab | **the URL** (`useSearchParams`) |
| Ephemeral UI | modal open, sidebar collapsed, form draft | `useState` in the nearest owner |
| Cross-cutting client state | colour scheme | Mantine's own provider |
| Anything else | — | it is probably one of the above |

### Redux is gone

`Fusion-client` keeps `user`, `role`, `accessibleModules` and `currentAccessibleModules` in Redux. Every one of
those comes from `GET /api/auth/me` and is invalidated by a server event — that is server state with extra
steps. Worse, `setCurrentAccessibleModules` derives one slice from another, so the store holds two
representations of the same fact and they can disagree.

In the shell, `useAuth()` reads a single `["session"]` query. There is nothing to keep in sync.

### Filters go in the URL

```tsx
const [params, setParams] = useSearchParams();
const status = params.get("status") ?? "published";
```

A coordinator can then share `/placement/applications?status=shortlisted&posting=812` with a colleague, the
back button works, and a refresh does not lose their place. Filters in `useState` cannot do any of that.

---

## Query keys

Namespaced tuples, coarse → fine, so prefix invalidation works:

```ts
["session"]
["placement", "postings", { status, company, cursor }]
["placement", "postings", postingId]
["placement", "postings", postingId, "applications", { status }]
["placement", "offers", "mine"]
["academics", "standing", userId]
```

Rules:

- **First segment is the module.** `queryClient.invalidateQueries({queryKey: ["placement"]})` then clears
  everything that module owns.
- Filter objects are the **last** segment, so partial prefixes stay usable.
- No dates or random values in a key — they break cache hits silently.
- Generated `orval` hooks already follow this. Hand-written keys must match, or invalidation misses them.

### Permission version in the key, where it matters

For data whose *visibility* depends on permissions:

```ts
["placement", "applications", { pv: session.permission_version, ...filters }]
```

A role switch bumps `pv`, so the cached coordinator-scoped list cannot be served to the same person acting as a
student. This mirrors the server's version-in-key cache strategy
([rbac-model.md](../02-iam/rbac-model.md#caching-and-why-invalidation-is-not-a-problem)) — the version changes,
the key changes, the stale entry is simply never read again.

On an actual role switch we also call `queryClient.clear()`, because blunt is correct there: a role switch is
rare, and a privileged list leaking into a lower-privileged view is not acceptable.

---

## `staleTime`

| Data | `staleTime` | Why |
|---|---|---|
| Reference data (tiers, categories, disciplines) | 10 min | changes monthly |
| The session (`/me`) | 5 min | plus refetch on window focus |
| Lists (postings, applications) | 30 s | a coordinator watching a queue expects near-live |
| A single record being edited | 0 | always fresh before a write |
| Statistics snapshots | 5 min | server-side they refresh every 15 min |

Defaults in `QueryProvider`: `staleTime: 30_000`, `retry: 1`, `refetchOnWindowFocus: true`,
`refetchOnReconnect: true`.

`retry: 1`, not the default 3. A 422 or 409 is a **deterministic** answer — retrying it three times just
delays the error the user needs to see. Only network-level failures are worth one retry, and the interceptor
already handles 401 via refresh.

---

## Mutations

```ts
const submit = useSubmitApplication({
  mutation: {
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["placement", "postings"] });
      qc.invalidateQueries({ queryKey: ["placement", "applications"] });
      notify.success("Application submitted");
      navigate(`/placement/applications/${data.id}`);
    },
    onError: (e) => notify.error(errorMessage(e)),
  },
});
```

**Invalidate by prefix, do not hand-patch the cache.** Writing the new row into a cached list means guessing
what the server computed — the assigned id, the derived status, the recomputed counters. Invalidation asks.

### Idempotency

Every creating mutation sends an `Idempotency-Key` (a UUIDv7 per user gesture, generated in the request
interceptor). A double-click, a flaky network or an impatient user pressing "Apply" twice is safe
([api-conventions.md](../01-architecture/api-conventions.md#idempotency)). The button is also disabled while
`isPending` — but the header is what actually guarantees it.

### Optimistic updates: rarely

Only for genuinely reversible, low-stakes toggles (marking a notification read). **Never** for:

- offer acceptance — it runs a policy check that can legitimately deny
- application submission — it runs eligibility guards
- any state-machine transition — the server may return 409

For these, the pending state is a spinner and the truth is the server's answer. An optimistic UI that shows
"Accepted!" before the policy check runs is worse than a 300 ms wait.

---

## Pagination

Cursor-based ([api-conventions.md](../01-architecture/api-conventions.md#lists--cursor-pagination-always)).
There is deliberately no `count`, so no "page 4 of 12".

```ts
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteListPostings(
  { status }, { query: { getNextPageParam: (last) => last.next ?? undefined } });
```

Infinite scroll for student-facing lists; an explicit "Load more" for coordinator tables, where losing your
scroll position mid-review is worse than clicking a button.

Where a total genuinely matters (a "142 applications" badge), it is a separate cached
`?with_count=true` request, and it is approximate above 10,000 — labelled as such.

---

## Loading and error states

Three distinct states, never collapsed into two:

```tsx
if (error)     return <ErrorState error={error} onRetry={refetch} />;
if (isPending) return <TableSkeleton rows={5} />;
if (!rows.length) return <EmptyState {...empty} />;
```

"No results" and "failed to load" look identical if you conflate them, and a user shown an empty table after a
500 will conclude their data is gone.

`ErrorState` always renders the **`request_id`** from the error envelope. That id is what turns a screenshot
into a `journalctl` grep.

Skeletons, not spinners, for content areas — the layout does not jump when data arrives.

---

## Errors from the envelope

```ts
export function errorMessage(e: unknown): string {
  const env = (e as AxiosError<ErrorEnvelope>)?.response?.data?.error;
  if (!env) return "Something went wrong. Please try again.";
  if (env.details?.length) return env.details.map(d => d.message).join(" ");
  return env.message;
}
```

Switch on `error.code` (stable), never on `error.message` (human-facing and translatable):

```ts
if (env.code === "already_placed")           show(<AlreadyPlacedExplainer decision={env.details} />);
else if (env.code === "step_up_required")    openReauthModal();
else if (env.code === "invalid_transition")  notify.error("This item has already moved on. Refreshing…");
```

The `already_placed` case is worth the special component: the server sends the persisted `policy_decision` with
the actual numbers, so the student sees *why* — "you hold a ₹12 LPA offer and the dream threshold is ₹20 LPA" —
rather than a flat refusal ([offer-and-tier-policy.md](../04-placement/offer-and-tier-policy.md)).

---

## Forms

`@mantine/form` with a zod resolver. Both existing clients have `@mantine/form` as a dependency and use raw
`useState` objects with a `handleChange(field, value)` instead — new code uses the library.

```tsx
const form = useForm({
  mode: "uncontrolled",
  validate: zodResolver(RaiseComplaintSchema),
  initialValues: { category: "", location: "", description: "" },
});
```

`mode: "uncontrolled"` avoids a re-render per keystroke on long forms.

Server-side field errors from `error.details` are mapped back onto the form:

```ts
onError: (e) => {
  const details = envelope(e)?.details ?? [];
  if (details.length) form.setErrors(Object.fromEntries(
    details.map(d => [d.field, d.message])));
  else notify.error(errorMessage(e));
}
```

Client validation is a convenience; the server is authoritative, and its field errors must land on the right
inputs rather than in a toast.

---

## Realtime

**There is none, and that is deliberate.** No websockets, no SSE, no polling by default. `refetchOnWindowFocus`
covers the realistic case — a coordinator returning to a tab gets current data.

Two exceptions, both bounded:

- An **offer countdown** ticks client-side from `respond_by`, corrected by `server_time` from `/me` so a skewed
  client clock cannot show the wrong deadline.
- An **async job** (`202` + `poll_url`) polls at 2 s, backing off to 10 s, and stops after 5 minutes with a
  "still running, we'll email you" message.

---

## Verification

- No `redux` or `zustand` in any `package.json` — asserted by a CI check.
- A role switch clears the cache: a test asserts a coordinator-scoped list is not served after switching to
  `student`.
- `pv` in the key: changing `permission_version` produces a cache miss.
- Prefix invalidation: a mutation test asserts the list refetches.
- Every creating mutation sends `Idempotency-Key` — asserted in an MSW handler.
- Loading, empty and error are three distinct rendered outputs per list page.
- `ErrorState` renders the `request_id`.
- Server field errors land on the correct inputs.
- `retry` is 1, and a 422 is not retried.
- Filters survive a page refresh (they are in the URL).
