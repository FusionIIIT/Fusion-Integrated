import { Alert } from "@mantine/core";

import { useAuth } from "./AuthProvider";

export function RequirePermission({
  code,
  children,
}: {
  code: string;
  children: React.ReactNode;
}) {
  const { can } = useAuth();

  if (!can(code)) {
    return <Alert color="red" title="Permission required">You do not have access to this page.</Alert>;
  }

  return <>{children}</>;
}
