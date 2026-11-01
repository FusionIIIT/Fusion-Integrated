from rest_framework.permissions import IsAdminUser, IsAuthenticated

# Any authenticated operator may read ERP data.
ReadOnly = [IsAuthenticated]

# Mutations and privileged actions (create/delete, bulk writes, schema changes,
# password resets, backup/restore) are restricted to staff operators.
Privileged = [IsAdminUser]
