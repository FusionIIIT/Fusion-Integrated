import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useAuditEvents, useComplianceRequest, useComplianceRequests, useMyServiceRecord,
  useNotifications, useOwnLeaveBalances, usePolicies, useRequestDetails, useRequests,
  useServiceRecord, useServiceRecords,
} from "./hooks";

const actor = vi.hoisted(() => ({ userId: 10, role: "hradmin" }));
const api = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ session: { user: { id: actor.userId }, active_role: actor.role } }),
}));
vi.mock("../../../lib/http", () => ({ http: api }));

afterEach(() => {
  api.get.mockReset();
  actor.userId = 10;
  actor.role = "hradmin";
});

describe("HR-EIS query cache confidentiality", () => {
  it("does not reuse another designation's request data after a role switch", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    api.get.mockImplementation(async () => ({ data: {
      results: [{ owner: actor.userId, designation: actor.role }],
    } }));
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result, rerender, unmount } = renderHook(() => useRequests(), { wrapper });

    await waitFor(() => expect(result.current.data?.results).toEqual([
      { owner: 10, designation: "hradmin" },
    ]));
    actor.role = "staff";
    rerender();
    // An old administrator response must never be rendered under staff's cache key.
    expect(result.current.data?.results).not.toEqual([
      { owner: 10, designation: "hradmin" },
    ]);
    await waitFor(() => expect(result.current.data?.results).toEqual([
      { owner: 10, designation: "staff" },
    ]));

    actor.userId = 11;
    rerender();
    expect(result.current.data?.results).not.toEqual([
      { owner: 10, designation: "staff" },
    ]);
    await waitFor(() => expect(result.current.data?.results).toEqual([
      { owner: 11, designation: "staff" },
    ]));

    expect(api.get).toHaveBeenCalledTimes(3);
    unmount();
    client.clear();
  });
});

describe("all HR-EIS read hooks", () => {
  it.each([
    ["my record", () => useMyServiceRecord()],
    ["records", () => useServiceRecords()],
    ["request list", () => useRequests()],
    ["notifications", () => useNotifications()],
    ["request details", () => useRequestDetails(42)],
    ["compliance list", () => useComplianceRequests()],
    ["audit", () => useAuditEvents()],
    ["policies", () => usePolicies()],
    ["leave balances", () => useOwnLeaveBalances()],
    ["employee record", () => useServiceRecord(42)],
    ["compliance detail", () => useComplianceRequest(42)],
  ] as const)("%s uses both identity and designation in its cache key", (_name, useRead) => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    api.get.mockResolvedValue({ data: { results: [] } });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { rerender, unmount } = renderHook(() => { useRead(); }, { wrapper });
    expect(client.getQueryCache().findAll({ queryKey: ["hreis", 10, "hradmin"] })).toHaveLength(1);

    actor.role = "staff";
    rerender();
    expect(client.getQueryCache().findAll({ queryKey: ["hreis", 10, "staff"] })).toHaveLength(1);

    actor.userId = 11;
    rerender();
    expect(client.getQueryCache().findAll({ queryKey: ["hreis", 11, "staff"] })).toHaveLength(1);
    unmount();
    client.clear();
    actor.userId = 10;
    actor.role = "hradmin";
  });
});
