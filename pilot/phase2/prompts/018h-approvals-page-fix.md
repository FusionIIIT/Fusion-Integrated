Review of ApprovalsPage.tsx after task 018d (tsc: 5 errors). The handler, actionsFor and the new column definitions are right, but the old pieces were kept as well: the old `const columns = [...]` array without render functions is still there and is spread into the table (every column appears twice), `data?.results` is read although useInbox returns a plain array, `Text` is used without being imported, TextInput gets a `clearable` prop it does not have, and Group gets `size` instead of `gap`. Fix only these, with SEARCH/REPLACE edits:

1. Delete the whole `  const columns = [` ... `  ];` block (the eight entries without render) and the blank line after it.
2. Delete the line `  const rowsData = data?.results || [];` and the blank line after it.
3. In the TextInput, replace the line `        clearable` with `        mb="md"`.
4. Replace
      {rowsData.length === 0 ? (
        <Card padding="lg">
          <Text>No pending approvals</Text>
        </Card>
      ) : (
        <DataTable<LeaveApplication>
with
      <Card padding="lg">
        <DataTable<LeaveApplication>
5. Delete the line `            ...columns,`.
6. In the Category column, replace `              return <Text>{categoryLabel}</Text>;` with `              return categoryLabel;`.
7. Replace `              <Group size="xs">` with `              <Group gap="xs">`, and add `size="xs"` to the Button inside it (on the line after `<Button`).
8. Replace the closing
        />
      )}
    </Container>
with
        />
      </Card>
    </Container>

Do not change anything else.
