TITLE: Replace the unused columns/rowsData block in ApprovalsPage with the rows filter
FORMAT: diff
EDIT: client/src/modules/leave/pages/ApprovalsPage.tsx
LIMIT: 600
POST: none
---
After task 018h tsc reports 4 errors in ApprovalsPage.tsx: `columns` and `rowsData` are declared but never used (and rowsData reads data?.results, which does not exist), while the DataTable uses `rows`, which is no longer declared (018h deleted the wrong line). Fix only this, with ONE SEARCH/REPLACE edit. Replace this whole block:

  const columns = [
    { key: "applicant", header: "Applicant" },
    { key: "category", header: "Category" },
    { key: "start_date", header: "Dates" },
    { key: "days", header: "Days" },
    { key: "purpose", header: "Purpose" },
    { key: "stage", header: "Stage" },
    { key: "unit_head_recommendation", header: "Unit Head recommendation" },
    { key: "actions", header: "Actions" },
  ];

  const rowsData = data?.results || [];

with this single line:

  const rows = (data ?? []).filter((a) => a.stage !== "substitute");

Do not change anything else.
