TITLE: Show the substitute's consent status instead of "Replaced by user" in My Leaves
FORMAT: diff
EDIT: client/src/modules/leave/pages/MyLeavesPage.tsx
LIMIT: 600
POST: none
---
Found in the end-to-end browser test: after the substitute ACCEPTED, the Substitute column on My Leaves reads "Replaced by user 102", which tells the applicant the opposite of what happened (EL-UC-002 says the applicant must see the substitute's consent status). Fix only this, with one SEARCH/REPLACE edit in the ReplaceSubstitute component: replace
          {substituteId ? `Replaced by user ${substituteId}` : "-"}
with
          {substituteId ? `User ${substituteId} (${status.replace(/_/g, " ")})` : "-"}
Do not change anything else.
