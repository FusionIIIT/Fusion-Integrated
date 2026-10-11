---
owner: frontend-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Module Authoring Guide — Frontend

Adding a module to the shell. Worked example: `complaints`, matching the backend example in
[module-authoring-guide.md](../03-platform/module-authoring-guide.md).

Read [design-system.md](design-system.md) and [navigation-contract.md](navigation-contract.md) first. The
backend module must exist, with its `registry_module` and `registry_nav_item` rows seeded — the frontend
consumes them.

```bash
pnpm gen:module complaints        # scaffolds steps 1–2
```

---

## Step 1 — Manifest

```ts
// apps/shell/src/modules/complaints/manifest.ts
import type { ModuleManifest } from "../registry";

export const manifest: ModuleManifest = {
  code: "complaints",                       // MUST equal registry_module.code
  basePath: "/complaints",                  // MUST equal registry_module.base_path
  load: () => import("./routes"),
  indexPermission: "complaints.complaint.view_self",
};
```

```ts
// apps/shell/src/modules/registry.ts
export const MODULE_REGISTRY: Record<string, ModuleManifest> = {
  dashboard:      dashboardManifest,
  placement_cell: placementManifest,
  complaints:     complaintsManifest,       // ← add here
  hr:             hrManifest,
  leave:          leaveManifest,
  profile:        profileManifest,
  sysops:         sysopsManifest,
};
```

`code` and `basePath` must match the backend exactly. `module_registry_parity` in CI asserts the key set equals
`registry_module.code`, and `nav_route_parity` asserts every `registry_nav_item.to` resolves to a route — so a
mismatch is a build failure, not a menu item that silently does nothing.

`load` must be a **static** `import()` literal. Vite cannot analyze a computed specifier, and the chunk will
not be split.

---

## Step 2 — Routes

```tsx
// apps/shell/src/modules/complaints/routes.tsx
import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { RequirePermission } from "@fusion/auth";

const MyComplaints  = lazy(() => import("./pages/MyComplaintsPage"));
const ComplaintQueue = lazy(() => import("./pages/ComplaintQueuePage"));
const ComplaintDetail = lazy(() => import("./pages/ComplaintDetailPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyComplaints /> },
  { path: "queue", element: (
      <RequirePermission code="complaints.complaint.view">
        <ComplaintQueue />
      </RequirePermission>
    ) },
  { path: ":id", element: <ComplaintDetail /> },
];
```

Paths are **relative** — the shell mounts them under `basePath`. A leading `/` would escape the module.

Route paths mirror `registry_nav_item.to` exactly. Note that the sysadmin client's route casing is
inconsistent (`/UserDirectory` next to `/dashboard`); new modules use **lowercase-kebab** throughout.

---

## Step 3 — Folder layout

Follow `pages/UpcomingBatches/` in the sysadmin client — the best-structured existing feature:

```
complaints/
├── manifest.ts
├── routes.tsx
├── pages/
│   ├── MyComplaintsPage.tsx        one file per route, thin: layout + hooks + components
│   ├── ComplaintQueuePage.tsx
│   └── ComplaintDetailPage.tsx
├── components/
│   ├── ComplaintTable.tsx          module-local
│   ├── RaiseComplaintModal.tsx
│   └── ComplaintStatusBadge.tsx
├── hooks/
│   ├── useComplaints.ts            wraps the generated query hook, adds filter state
│   └── useComplaintActions.ts      mutations + invalidation
├── api/                            only if the generated client needs shaping
└── utils/
    └── formatters.ts
```

**Pages are thin.** A page composes a layout, a hook and some components. Business logic in a page component
cannot be tested without rendering it — which is how a 1,709-line `login.jsx` happens.

Anything genuinely reusable is promoted to `@fusion/ui` rather than copied into a second module.

---

## Step 4 — A page

```tsx
// pages/ComplaintQueuePage.tsx
export default function ComplaintQueuePage() {
  const { complaints, isPending, error, filters, setFilters } = useComplaints();
  const { assign } = useComplaintActions();
  const { can } = usePermission();

  if (error) return <ErrorState error={error} />;

  return (
    <Container size="xl">
      <PageHeader
        title="Complaint Queue"
        subtitle="Open complaints awaiting assignment"
        action={can("complaints.complaint.assign")
          ? <Button leftSection={<FaUserPlus size={13} />} onClick={openAssign}>Assign</Button>
          : null}
      />
      <Card padding="lg">
        <ComplaintFilters value={filters} onChange={setFilters} />
        <DataTable
          rows={complaints}
          loading={isPending}
          minWidth={860}
          columns={[
            { key: "id",       header: "#" },
            { key: "category", header: "Category" },
            { key: "location", header: "Location" },
            { key: "status",   header: "Status",
              render: r => <ComplaintStatusBadge status={r.status} /> },
            { key: "created_at", header: "Raised",
              render: r => <DateText value={r.created_at} relative /> },
          ]}
          actions={r => [{ icon: FaEye, label: "Open", onClick: () => go(r.id) }]}
          empty={{ icon: FaCheckCircle, title: "Queue is clear",
                   description: "No open complaints right now." }}
        />
      </Card>
    </Container>
  );
}
```

`<Container size="xl">` → `<PageHeader>` → `<Card padding="lg">`. No `radius` or `shadow` props — the theme
supplies them, and overriding is a visual regression.

`can(...)` hides the button. The server enforces the permission regardless; **this is UX only**.

Every table has an explicit `empty` state. A bare "No data" is a review rejection.

---

## Step 5 — A data hook

```ts
// hooks/useComplaints.ts
export function useComplaints() {
  const [filters, setFilters] = useState<ComplaintFilters>({ status: "open" });
  const debounced = useDebouncedValue(filters, 200);

  const query = useListComplaints(debounced, {           // generated by orval
    query: { staleTime: 30_000, placeholderData: keepPreviousData },
  });

  return { complaints: query.data?.results ?? [], isPending: query.isPending,
           error: query.error, filters, setFilters };
}
```

```ts
// hooks/useComplaintActions.ts
export function useComplaintActions() {
  const qc = useQueryClient();
  const assign = useAssignComplaint({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ["complaints"] });   // prefix invalidation
        notify.success("Complaint assigned");
      },
      onError: (e) => notify.error(errorMessage(e)),          // reads the error envelope
    },
  });
  return { assign };
}
```

`placeholderData: keepPreviousData` keeps the previous page visible while a filter change loads, instead of
flashing a skeleton. Conventions: [state-and-data-fetching.md](state-and-data-fetching.md).

---

## Step 6 — Tests

```tsx
// pages/__tests__/ComplaintQueuePage.test.tsx
import { renderWithProviders } from "@fusion/testing";

it("shows the empty state when the queue is clear", async () => {
  server.use(http.get("*/complaints", () => HttpResponse.json({ results: [], next: null })));
  renderWithProviders(<ComplaintQueuePage />, { permissions: ["complaints.complaint.view"] });
  expect(await screen.findByText("Queue is clear")).toBeInTheDocument();
});

it("hides Assign without the permission", async () => {
  renderWithProviders(<ComplaintQueuePage />, { permissions: ["complaints.complaint.view"] });
  await screen.findByRole("table");
  expect(screen.queryByRole("button", { name: /assign/i })).not.toBeInTheDocument();
});
```

`renderWithProviders` supplies Mantine, TanStack Query, a `MemoryRouter` and a mock `AuthProvider` with the
permissions you name. MSW handlers are **generated from the OpenAPI examples**, so a mock cannot drift from
the real API — which is the failure mode that makes frontend tests worthless.

Coverage targets: `packages/*` 70%, `apps/shell` 60%.

---

## Step 7 — E2E, for the critical path only

```ts
// e2e/complaints.spec.ts
test("a student raises a complaint and sees it in their list", async ({ page }) => {
  await loginAs(page, "student");
  await page.getByRole("link", { name: "Complaints" }).click();
  await page.getByRole("button", { name: "Raise complaint" }).click();
  await page.getByLabel("Category").selectOption("Electrical");
  await page.getByLabel("Location").fill("Hall 3, Room 210");
  await page.getByLabel("Description").fill("Ceiling fan not working");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Complaint raised")).toBeVisible();
  await expect(page.getByRole("cell", { name: /Hall 3, Room 210/ })).toBeVisible();
});
```

One happy path plus the module's single most important failure path. E2E is expensive; the rest belongs in
vitest.

---

## Definition of done

- [ ] `manifest.code` === `registry_module.code`; `basePath` === `base_path`
- [ ] Registered in `MODULE_REGISTRY`; all four parity checks pass
- [ ] `load` is a static `import()`; a `module-complaints` chunk appears in the build
- [ ] Route paths relative, lowercase-kebab, matching every `registry_nav_item.to`
- [ ] Pages thin; logic in hooks; nothing duplicating `@fusion/ui`
- [ ] `<Container>` → `<PageHeader>` → `<Card padding="lg">`, no theme-overriding props
- [ ] Every table has an explicit `empty`; every page has an `ErrorState` path
- [ ] `RequirePermission` on privileged routes; `can()` for buttons — server enforces both
- [ ] `notify.success` / `notify.error`, not raw `notifications.show`
- [ ] Money via `<Money/>`; dates via `<DateText/>` (a CPI must show its provenance — see below)
- [ ] Tests at target coverage; MSW handlers from OpenAPI examples
- [ ] One E2E happy path
- [ ] `size-limit` under 150 kB gz for the chunk
- [ ] `axe-core` clean; keyboard-navigable
- [ ] Module granted to roles, and `registry_module.status` flipped to `active` **last**

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `code` mismatch with the backend | CI parity check fails | make them equal |
| Computed `import()` in `load` | no chunk split; whole module in the entry bundle | static literal |
| Absolute route paths | route escapes the module mount | relative paths |
| `<Card radius="md">` | visual regression the theme cannot prevent | drop the prop |
| `import * as Fa` | ~1 MB of icons shipped | named imports; ESLint bans it |
| Business logic in a page component | untestable without rendering | move to a hook |
| Relying on `can()` alone | **the endpoint is still open** | add the server permission |
| Copying a component from another module | two copies diverge | promote to `@fusion/ui` |
| `status = "active"` too early | a half-built module is visible in production | flip it last |
| Rendering a bare CPI number | "my CPI is wrong" tickets | always `8.10 · Sem 5 (Odd) · declared 28 Jul 2026` — [academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md#8-provenance-on-screen) |
