import { Container, Loader } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { createContext, type ReactNode, useContext, useEffect, useRef } from "react";
import { Outlet } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { ErrorState } from "../../ui/components/ErrorState";
import { NotPermitted } from "../../ui/components/NotPermitted";
import { useDepartmentFeed, useDepartmentRecord } from "./api";

interface Notice { id: number; message: string }
const DepartmentPermissions = createContext<readonly string[]>([]);

export function useDepartmentCan() {
  const permissions = useContext(DepartmentPermissions);
  return (code: string) => permissions.includes(code);
}

export function RequireDepartmentPermission({ permission, children }: { permission: string; children: ReactNode }) {
  const can = useDepartmentCan();
  return can(permission) ? children : <Container size="md" py="lg"><NotPermitted /></Container>;
}

function NoticeObserver() {
  const feed = useDepartmentFeed<Notice>("notices", 15000);
  const mostRecent = useRef<number | null>(null);
  const firstPage = feed.data?.pages[0]?.results;

  useEffect(() => {
    if (!firstPage) return;
    const previous = mostRecent.current;
    mostRecent.current = Math.max(previous ?? 0, firstPage[0]?.id ?? 0);
    if (previous === null) return;
    for (const notice of firstPage.filter((row) => row.id > previous).reverse()) {
      notifications.show({ message: notice.message });
    }
  }, [firstPage]);

  return null;
}

export function DepartmentLayout() {
  const { session } = useAuth();
  const access = useDepartmentRecord<{ permissions: string[] }>("access");
  if (access.isPending) return <Container size="md" py="lg"><Loader aria-label="Loading Department access" /></Container>;
  if (access.isError) return <Container size="md" py="lg"><ErrorState error={access.error} /></Container>;
  return (
    <DepartmentPermissions.Provider value={access.data.permissions}>
      {access.data.permissions.includes("department.notice.view") && (
        <NoticeObserver key={`${session?.user.id}:${session?.active_role}`} />
      )}
      <Outlet />
    </DepartmentPermissions.Provider>
  );
}
