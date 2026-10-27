TITLE: Fix the unclosed DataTable tag in SubstituteRequestsPage left by 018e
FORMAT: diff
EDIT: client/src/modules/leave/pages/SubstituteRequestsPage.tsx
LIMIT: 600
POST: none
---
Task 018e left the DataTable element unclosed: its attributes end with `empty={{ ... }}` and are followed by `</DataTable>`, so tsc reports "Expected corresponding JSX closing tag for 'Card'". DataTable takes no children; it must be self-closing. Fix only this, with one SEARCH/REPLACE edit: replace the line
        </DataTable>
with
        />
Do not change anything else.
