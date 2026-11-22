import { Container } from "@mantine/core";

import { NotPermitted } from "../ui/components/NotPermitted";
import { useAuth } from "./AuthProvider";

/** A route only some roles may use: anyone else gets NotPermitted, and the page never mounts. */
export function RequirePermission({ permission, children }: {
  permission: string;
  children: React.ReactNode;
}) {
  const { can } = useAuth();
  if (!can(permission)) {
    return <Container size="xl" pt="md"><NotPermitted /></Container>;
  }
  return <>{children}</>;
}
