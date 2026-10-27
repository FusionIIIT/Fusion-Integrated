TITLE: Add the two missing imports in SubstituteRequestsPage
FORMAT: diff
EDIT: client/src/modules/leave/pages/SubstituteRequestsPage.tsx
LIMIT: 600
POST: none
---
tsc reports 10 errors in SubstituteRequestsPage.tsx; they all come from two missing imports: `Text` is used but not imported ("'Text' cannot be used as a JSX component"), and `Column` is used in `const columns: Column<LeaveApplication>[]` but not imported (which also makes every `row` parameter implicitly any). Fix only these, with two SEARCH/REPLACE edits:

1. Change `import { Button, Card, Container, Group } from "@mantine/core";` to `import { Button, Card, Container, Group, Text } from "@mantine/core";`.
2. Change `import { DataTable } from "../../../ui/components/DataTable";` to `import { DataTable, type Column } from "../../../ui/components/DataTable";`.

Do not change anything else.
