import { Center, Container, Loader } from "@mantine/core";
import type { ReactNode } from "react";

import { NotPermitted } from "../../../ui/components/NotPermitted";
import { useActing } from "../api/hooks";

// PMS permissions of the role the person is acting as; nothing is allowed until known.
export function usePmsCan(): (permission: string) => boolean {
  const acting = useActing();
  const held = new Set(acting.data?.permissions ?? []);
  return (permission: string) => held.has(permission);
}

// A PMS page for one acting role: anyone else gets NotPermitted and the page never mounts.
export function PmsGuard({ permission, children }: { permission: string; children: ReactNode }) {
  const acting = useActing();
  if (acting.isPending) return <Center py="xl"><Loader size="sm" /></Center>;
  if (!acting.data?.permissions.includes(permission)) {
    return <Container size="xl" pt="md"><NotPermitted /></Container>;
  }
  return <>{children}</>;
}
