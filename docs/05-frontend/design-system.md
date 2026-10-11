---
owner: frontend-lead
status: authoritative
last-reviewed: 2026-08-01
verified-by: Playwright screenshot baselines captured from the live /sysadmin/ client
---

# Design System — `@fusion/ui`

The requirement was that the UI be **exactly** the `Fusion_System_Administrator` UI. So this design system is
**extracted, not designed**. Nothing here is a new visual decision.

`packages/ui/src/layout/AppShellLayout.module.css` is a **byte-identical copy** of
`Fusion_System_Administrator/client/src/components/AppLayout/AppLayout.module.css`. That file *is* the visual
contract, and Playwright screenshot baselines captured from the live `/sysadmin/` client prove it — the
extraction is verified, not asserted.

---

## Extraction map

| Source (existing) | Destination | Transformation |
|---|---|---|
| `client/src/theme.js` | `packages/ui/src/theme/theme.ts` | **Verbatim**, typed as `MantineThemeOverride` |
| `client/src/components/AppLayout/AppLayout.module.css` | `packages/ui/src/layout/AppShellLayout.module.css` | **Byte-identical copy** |
| `client/src/components/AppLayout/AppLayout.jsx` | `packages/ui/src/layout/AppShellLayout.tsx` | Props replace imports. Markup, class names, sizes and `AppShell` config unchanged. |
| `client/src/components/AppLayout/navConfig.jsx` | **deleted** — its shape becomes the server contract | `ALL_LINKS` becomes a `useMemo(flattenNav)` inside the component |
| `client/src/pages/Login/constants.js` (`BRAND`, `NOTIFICATION_STYLES`) | `packages/ui/src/theme/{brand,notifications}.ts` | Verbatim |
| `client/src/components/PageHeader/PageHeader.jsx` | `packages/ui/src/components/PageHeader.tsx` | Typed props |
| `client/src/components/Stats*/**` | `packages/ui/src/components/Stats*` | Typed; CSS modules copied |
| `client/src/charts/**` | `packages/ui/src/charts/**` | Typed |
| `client/src/pages/UpcomingBatches/components/BatchTable.jsx` | distilled → `components/DataTable.tsx` | Generalize the pattern |
| `client/src/pages/UpcomingBatches/components/AddBatchModal.jsx` | distilled → `components/FormModal.tsx` | Generalize the pattern |
| `client/src/context/axiosInstance.jsx` | `packages/api-client/src/http.ts` | Adds CSRF, request-id, single-flight refresh |
| `client/src/context/AuthContext.jsx` | `packages/auth/src/AuthProvider.tsx` | Keeps the `storage`-event cross-tab logout and throttled idle timer |
| `client/src/pages/Login/**` | `apps/shell/src/pages/Login/**` | Already componentized — port to TS as-is |

**Do not salvage `Fusion-client/src/pages/login.jsx`** (1,709 lines, one component). The sysadmin login is
already split into `components/` + `hooks/` + `constants.js` and is the one to port.

---

## Tokens

### Theme — `packages/ui/src/theme/theme.ts`

```ts
const SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

export const theme: MantineThemeOverride = createTheme({
  primaryColor: "blue",
  primaryShade: { light: 6, dark: 5 },
  fontFamily: SANS,
  headings: { fontFamily: SANS, fontWeight: "600" },
  defaultRadius: "md",
  components: {
    Card:   { defaultProps: { radius: "lg", withBorder: true, shadow: "sm" } },
    Paper:  { defaultProps: { radius: "lg" } },
    Button: { defaultProps: { radius: "md" } },
    Table:  { defaultProps: { highlightOnHover: true, verticalSpacing: "sm" } },
    Modal:  { defaultProps: { radius: "lg", centered: true, overlayProps: { blur: 2 } } },
  },
});
```

The `components` block is the reason the UI looks consistent without anyone thinking about it: a plain
`<Card>` is already `radius="lg" withBorder shadow="sm"`. **Do not pass those props again at call sites** — a
`<Card radius="md">` is a visual regression the theme cannot protect you from.

### Brand — `packages/ui/src/theme/brand.ts`

```ts
export const BRAND = Object.freeze({
  primary:    "#15ABFF",
  dark:       "#111111",
  danger:     "#FA5252",
  surface:    "#FFFFFF",
  surfaceAlt: "#F8F9FA",
  border:     "#E9ECEF",
  gridLine:   "#DEE2E6",
});
```

`#15ABFF` is the accent throughout — the sidebar active state, the brand rule, focus rings.

### Sidebar palette — `AppShellLayout.module.css`, unchanged

```css
.navbar { background: linear-gradient(180deg, #0c1526 0%, #080d18 100%); }
.header { background: rgba(255,255,255,.98);
          backdrop-filter: blur(20px) saturate(180%);
          border-bottom: 2px solid #0b1220; }
.brand  { border-left: 3px solid #15abff; padding-left: 14px;
          background: linear-gradient(90deg, rgba(21,171,255,.06) 0%, transparent 100%); }
.sectionLabel { color: rgba(255,255,255,.34); font-size: .62rem; font-weight: 700;
                letter-spacing: .16em; text-transform: uppercase; padding: 16px 10px 6px; }
.navLink { color: rgba(255,255,255,.68); border-radius: 9px; font-size: .9rem; }
.navLink[data-active] { background-color: rgba(21,171,255,.14); color: #fff;
                        box-shadow: inset 2px 0 0 0 #15abff; }
```

### Notification gradients — verbatim

Success `#10B981 → #059669`; error `#FF6B35 → #F7931E`. Byte-identical to both existing clients' toasts.

### Spacing, radius, breakpoints

Mantine defaults, unmodified. `defaultRadius: "md"`, with `Card`/`Paper`/`Modal` at `lg` via the theme.
Breakpoints: `xs 36em · sm 48em · md 62em · lg 75em · xl 88em` (Mantine defaults, from
`postcss-preset-mantine`).

> `Fusion-client`'s `App.jsx` adds custom breakpoints (`xxs: 300px`, `xs: 375px`, …). Those are **not**
> carried over — the sysadmin client uses Mantine defaults, and matching it is the requirement.

---

## Layout — the exact spec

```
┌───────────────────────────────────────────────────────────────────────┐
│ header · 66px · white 98% · blur(20px) saturate(180%)                  │
│          border-bottom: 2px solid #0b1220                             │
│  [burger<sm] [logo 40px] │ PDPM IIITDM JABALPUR                       │
│                          │ FUSION · <SUBTITLE>   (monospace, ls 2)    │
│                                        [role switcher] [date] [Logout]│
├──────────────────┬────────────────────────────────────────────────────┤
│ navbar · 280px   │ AppShell.Main · bg gray.0 · padding lg             │
│ #0c1526→#080d18  │                                                    │
│                  │  <Container size="xl">                             │
│ [search input]   │    <PageHeader title subtitle action />            │
│                  │    <Card padding="lg">  ...  </Card>               │
│ OVERVIEW         │  </Container>                                      │
│  ▸ Dashboard     │                                                    │
│ PLACEMENT        │                                                    │
│  ▾ Placement     │                                                    │
│     Job Postings │                                                    │
│     Applications │                                                    │
│                  │                                                    │
│ [operator card]  │                                                    │
└──────────────────┴────────────────────────────────────────────────────┘
```

Fixed values, none negotiable: header **66px** · navbar **280px** · main `bg="gray.0"` · padding `lg` ·
navbar collapses below `sm` behind a `Burger` with an overlay · **no breadcrumbs** anywhere · brand block
hidden below `xs` · date hidden below `sm`.

Page identity is carried by `PageHeader`, not breadcrumbs. That is the sysadmin client's choice and we keep
it.

### `AppShellLayout` props

```ts
export type IconKey = keyof typeof ICON_REGISTRY;
export interface NavLinkItem  { code: string; label: string; icon: IconKey; to: string }
export interface NavGroupItem { code: string; label: string; icon: IconKey; to?: string;
                                links?: NavLinkItem[] }
export interface NavGroup     { section: string; items: NavGroupItem[] }

export interface AppShellLayoutProps {
  navGroups: NavGroup[];                 // straight from GET /me — no client filtering
  activePath: string;
  onNavigate: (to: string) => void;
  brandTitle: React.ReactNode;           // "PDPM IIITDM " + <span>JABALPUR</span>
  brandSubtitle: string;                 // "FUSION · NON-ACADEMIC PLATFORM"
  logoSrc: string;
  user: { name: string; roleLabel: string };
  headerRightSlot?: React.ReactNode;     // RoleSwitcher + date + Logout
  footerSlot?: React.ReactNode;
  onLogout: () => void;
  externalLinks?: NavLinkItem[];         // "Academics (legacy)" while it lives outside
  children: React.ReactNode;
}
```

Everything the CSS controls stays in the CSS. The props exist only to replace what the original component
hardcoded (its nav config, its logo import, its logout handler).

`onNavigate` rather than an internal `useNavigate` keeps `packages/ui` router-agnostic and testable without a
router.

### Navigation behaviour, preserved exactly

- **Live search** over the flattened link list; matches render with their parent as `description`; no matches
  shows a dimmed "No matches" centered.
- **Single-level accordion** — one group open at a time, seeded from the current pathname.
- Active state: `rgba(21,171,255,.14)` background + `inset 2px 0 0 0 #15abff`.
- Section labels uppercase, `rgba(255,255,255,.34)`, letter-spacing `.16em`.

---

## Icons

Server sends `"FaBriefcase"`; the client resolves it.

```ts
// packages/ui/src/icons/index.ts
import { FaThLarge, FaBook, FaBriefcase, FaCircle, /* ~60 named imports */ } from "react-icons/fa";
export const ICON_REGISTRY = { FaThLarge, FaBook, FaBriefcase, /* … */ } as const;
export const resolveIcon = (k: string) => ICON_REGISTRY[k as IconKey] ?? FaCircle;
```

**Named imports only.** `import * as Fa from "react-icons/fa"` defeats tree-shaking and ships roughly a
megabyte. An ESLint rule bans the namespace form.

A CI check asserts every `registry_nav_item.icon` in the database resolves in `ICON_REGISTRY`, so a typo fails
the build instead of silently rendering a fallback circle.

---

## Component inventory

### `PageHeader` — on every page

```tsx
<PageHeader title="Job Postings"
            subtitle="Published openings for 2026-27"
            action={<Button leftSection={<FaPlus size={13}/>}>New posting</Button>} />
```

`<Group justify="space-between" align="flex-end" mb="lg">` → `<Title order={2}>` + dimmed `<Text size="sm">`
+ right-aligned action slot. Verbatim from the original.

### `DataTable` — distilled from `BatchTable.jsx`

Generalizes the house table pattern: `Table.ScrollContainer minWidth={…}` · inline `Badge` for enums ·
inline `Progress` for fill ratios · right-aligned `ActionIcon` group in `Tooltip`s · **an explicit empty
state** (`Center` + `ThemeIcon` + copy, never a bare "No data").

```tsx
<DataTable
  rows={postings}
  minWidth={860}
  columns={[
    { key: "title",  header: "Role",    render: r => <Text fw={600}>{r.title}</Text> },
    { key: "status", header: "Status",  render: r => <StatusBadge status={r.status}/> },
    { key: "seats",  header: "Filled",  align: "right",
      render: r => <Progress value={r.filled_pct} size="sm" w={90}/> },
  ]}
  actions={r => [{ icon: FaEye, label: "View", onClick: () => go(r.id) }]}
  empty={{ icon: FaClipboardList, title: "No postings yet",
           description: "Published postings will appear here." }}
/>
```

### `FormModal` — distilled from `AddBatchModal.jsx`

`padding={0}` · `withCloseButton={false}` · a custom gradient header band · `Stack p="lg"` body · footer
`Group justify="flex-end" p="md"` with a top border and `bg="var(--mantine-color-body)"`.

```tsx
<Box p="lg" style={{ background: "linear-gradient(135deg, var(--mantine-color-indigo-7), var(--mantine-color-blue-9))", color: "white" }}>
```

Simple confirmations use `ConfirmDialog` (a plain `<Modal title>`), matching `ManageRoleAccessPage.jsx`.

### The rest

`StatusBadge` (one status→colour map per domain, so the same status is never two colours) · `ActionMenu` ·
`EmptyState` · `ErrorState` · `StatsGrid` / `StatsRing` / `StatsSegments` / `StatsGroup` / `StatsControls`
(ported from the sysadmin client, where they exist but are currently unused by any page) ·
`FileDropzone` · `Money` (decimal-string safe — never a float) · `DateText` ·
`BarChartSimple` / `PieChartTooltip`.

`notify.ts` wraps `notifications.show()` with the exact success/error gradients.

---

## Page skeleton

```tsx
export function PostingListPage() {
  return (
    <Container size="xl">
      <PageHeader title="Job Postings" subtitle="…" action={…} />
      <Card padding="lg">
        <DataTable … />
      </Card>
    </Container>
  );
}
```

`<Container size="xl">` for tables and dashboards, `"lg"` for forms. `<Card padding="lg">` or
`<Paper p="lg">` for content — radius and border come from the theme.

### Forms

The house style, from `FacultyCreationPage.jsx`: a `Progress` completion bar driven by filled-field count,
then `Text tt="uppercase" c="dimmed"` section headers + `Divider` + `Grid gutter="md"` with
`Grid.Col span={{ base: 12, sm: 6 }}`, `size="md"` inputs, submit in `Group justify="flex-end"`.

**New code uses `@mantine/form`.** It is a dependency in both existing clients but unused — pages hand-roll
`useState` objects with a `handleChange(field, value)`. New forms use `useForm` with a zod resolver so
validation is declarative and typed. The *visual* pattern above is unchanged; only the state handling
improves.

---

## Do / don't

| Do | Don't |
|---|---|
| `<Card padding="lg">` | `<Card radius="md" shadow="xs">` — fights the theme |
| `BRAND.primary` or `var(--mantine-color-blue-6)` | a raw `#15abff` in a component |
| `notify.success(...)` | `notifications.show({color:"green"})` — loses the gradient |
| `<Money value={ctc}/>` | `{ctc.toFixed(2)}` — `ctc` is a decimal **string** |
| An explicit `empty` prop on every table | a bare "No data" |
| `resolveIcon(code)` | `import * as Fa` |
| Extend `packages/ui` | a bespoke component in a module that duplicates one |
| `<Container size="xl">` | a raw `<div style={{maxWidth}}>` |
| Named `react-icons/fa` imports | icons from a second icon library |

---

## Verification

**Visual regression is the proof.** Playwright `expect(page).toHaveScreenshot()` at 3 breakpoints
(`375`, `768`, `1440`), with baselines captured from the **live `/sysadmin/` client**.

Run **only inside a pinned Docker image** — host font rendering differs between macOS and Linux, and
regenerating baselines from a laptop is how these tests become noise everyone ignores.

Also asserted:

- Header is exactly 66px; navbar exactly 280px at ≥ `sm`.
- The navbar collapses below `sm` and the burger appears.
- Active nav item has `box-shadow: inset 2px 0 0 0 #15abff`.
- Sidebar search filters the flattened list and shows the parent as description.
- The accordion keeps at most one group open.
- **No breadcrumb element exists** anywhere in the shell.
- `axe-core` finds zero critical accessibility violations on every page; nav is keyboard-traversable; focus
  rings are visible against the dark navbar.
- `size-limit`: shell entry ≤ 220 kB gz, each module chunk ≤ 150 kB gz.
- Every `ICON_REGISTRY` key used by seeded `registry_nav_item` rows resolves.
