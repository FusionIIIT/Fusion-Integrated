// Test harness wrapping PSM pages in real Mantine, QueryClient, Router, and AuthProvider.
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

import { AuthProvider } from "../../auth/AuthProvider";

export function renderPsmPage(ui: ReactNode, permissions: string[] = []) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  qc.setQueryData(["session"], {
    user: { id: 1, username: "emp1", display_name: "Test User", kind: "faculty" },
    active_role: "ps_admin",
    roles: ["ps_admin"],
    modules: ["psm"],
    permissions,
    navigation: [],
    csrf_token: "test-csrf",
  });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>{ui}</AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
}
