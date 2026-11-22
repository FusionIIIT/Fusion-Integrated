import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import * as downloads from "../../../lib/download";
import { errorMessage, http } from "../../../lib/http";
import { useLmsDownload, useLmsList } from "./hooks";
import { AuthProvider } from "../../../auth/AuthProvider";
import type { Session } from "../../../auth/types";

const session: Session = { user: { id: 1, username: "synthetic", display_name: "Synthetic", kind: "student", email: "" },
  active_role: "student", roles: ["student", "faculty"], permissions: [], modules: ["lms"], navigation: [], csrf_token: "fixture" };

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  client.setQueryData(["session"], session);
  return <MemoryRouter><QueryClientProvider client={client}><AuthProvider>{children}</AuthProvider></QueryClientProvider></MemoryRouter>;
}
afterEach(() => vi.restoreAllMocks());

it("loads later cursor pages without dropping earlier courses", async () => {
  vi.spyOn(http, "get").mockResolvedValueOnce({ data: { results: [{ id: 1 }], next: "http://localhost:8002/api/v1/lms/courses/?cursor=next" } })
    .mockResolvedValueOnce({ data: { results: [{ id: 2 }], next: null } });
  const { result } = renderHook(() => useLmsList<{ id: number }>("/lms/courses/"), { wrapper });
  await waitFor(() => expect(result.current.items).toEqual([{ id: 1 }]));
  await act(async () => { await result.current.fetchNextPage(); });
  await waitFor(() => expect(result.current.items).toEqual([{ id: 1 }, { id: 2 }]));
  expect(http.get).toHaveBeenLastCalledWith("/lms/courses/?cursor=next");
});

it("downloads bytes through the shared client and uses the server filename", async () => {
  const blob = new Blob(["work"]);
  vi.spyOn(http, "get").mockResolvedValue({ data: blob, headers: { "content-disposition": "attachment; filename=work.txt" } });
  vi.spyOn(downloads, "saveBlob").mockImplementation(() => undefined);
  const { result } = renderHook(() => useLmsDownload(), { wrapper });
  await act(async () => { await result.current.mutateAsync({ path: "/lms/materials/1/download/", fallback: "material" }); });
  expect(downloads.saveBlob).toHaveBeenCalledWith(blob, "work.txt");
});

it("decodes a download refusal instead of saving the error as a file", async () => {
  vi.spyOn(http, "get").mockRejectedValue({ response: { data: new Blob([JSON.stringify({ error: { message: "Not permitted" } })]) } });
  vi.spyOn(downloads, "saveBlob").mockImplementation(() => undefined);
  const { result } = renderHook(() => useLmsDownload(), { wrapper });
  await act(async () => {
    await expect(result.current.mutateAsync({ path: "/lms/materials/1/download/", fallback: "material" })).rejects.toBeDefined();
  });
  await waitFor(() => expect(errorMessage(result.current.error)).toBe("Not permitted"));
  expect(downloads.saveBlob).not.toHaveBeenCalled();
});

it("does not reuse a faculty grade cache while switching to student", async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["session"], { ...session, active_role: "faculty" });
  vi.spyOn(http, "get").mockResolvedValueOnce({ data: { results: [{ secret: "draft" }], next: null } })
    .mockReturnValue(new Promise(() => undefined));
  function scopedWrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter><QueryClientProvider client={client}><AuthProvider>{children}</AuthProvider></QueryClientProvider></MemoryRouter>;
  }
  const { result } = renderHook(() => useLmsList<{ secret: string }>("/lms/courses/1/grades/"), { wrapper: scopedWrapper });
  await waitFor(() => expect(result.current.items).toEqual([{ secret: "draft" }]));
  act(() => { client.setQueryData(["session"], session); });
  await waitFor(() => expect(result.current.items).toEqual([]));
  expect(result.current.isPending).toBe(true);
});
