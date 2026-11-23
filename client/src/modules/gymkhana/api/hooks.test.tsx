/** The data layer alone: paging, refetching, partial approval, uploads and downloads. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import { access, club, led, membership, mockHttp, page, refusal } from "../test/harness";
import {
  useAccess, useApproveMemberships, useBook, useClubs, useConfirmClub, useDownload, usePeople,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => { vi.restoreAllMocks(); });

describe("lists", () => {
  it("follows the server's cursor and joins the pages", async () => {
    const pages = [
      { ...page(club), next: "http://testserver/api/v1/gymkhana/clubs/?cursor=abc" },
      page({ ...club, id: 2, name: "Chess Club" }),
    ];
    mockHttp({ "/gymkhana/clubs/": () => pages.shift() });

    const { result } = renderHook(() => useClubs(), { wrapper });
    await waitFor(() => { expect(result.current.hasMore).toBe(true); });
    act(() => { result.current.loadMore(); });

    await waitFor(() => {
      expect(result.current.rows.map((c) => c.name)).toEqual(["Robotics Club", "Chess Club"]);
    });
    expect(http.get).toHaveBeenLastCalledWith("/gymkhana/clubs/", { params: { cursor: "abc" } });
    expect(result.current.hasMore).toBe(false);
  });

  it("refetches after a write", async () => {
    mockHttp({ "/gymkhana/clubs/": page(club) }, { "/gymkhana/clubs/1/confirm/": club });

    const { result } = renderHook(
      () => ({ clubs: useClubs(), confirm: useConfirmClub() }), { wrapper });
    await waitFor(() => { expect(result.current.clubs.loading).toBe(false); });
    act(() => { result.current.confirm.mutate(1); });

    await waitFor(() => { expect(http.get).toHaveBeenCalledTimes(2); });
  });
});

describe("useAccess", () => {
  it("answers by permission code and lists the clubs led", async () => {
    mockHttp({ "/gymkhana/access/": access(["gymkhana.poll.vote"], [led]) });

    const { result } = renderHook(() => useAccess(), { wrapper });

    await waitFor(() => { expect(result.current.loading).toBe(false); });
    expect(result.current.can("gymkhana.poll.vote")).toBe(true);
    expect(result.current.can("gymkhana.club.approve")).toBe(false);
    expect(result.current.clubsLed).toEqual([led]);
  });
});

describe("usePeople", () => {
  it("does not search until three characters are typed", () => {
    mockHttp({});
    renderHook(() => usePeople("as", "student"), { wrapper });
    expect(http.get).not.toHaveBeenCalled();
  });
});

describe("useApproveMemberships", () => {
  it("keeps the approvals that went through when one is refused", async () => {
    const refused = refusal(409, "Already decided");
    mockHttp({}, {
      "/gymkhana/memberships/7/approve/": membership,
      "/gymkhana/memberships/8/approve/": refused,
    });

    const { result } = renderHook(() => useApproveMemberships(), { wrapper });
    act(() => { result.current.mutate({ ids: [7, 8], remarks: "ok" }); });

    await waitFor(() => { expect(result.current.isSuccess).toBe(true); });
    expect(result.current.data).toEqual({ approved: 1, refusal: refused });
  });
});

describe("useBook", () => {
  it("sends a form without the fields left empty", async () => {
    const post = mockHttp({}, { "/gymkhana/bookings/session/": {} });

    const { result } = renderHook(() => useBook(), { wrapper });
    act(() => {
      result.current.mutate({
        kind: "session", club_id: 1, venue: "Hall 1", booking_date: "2026-12-10",
        start_time: "10:00", end_time: "11:00", name: "Practice", description: "",
        faculty_councillor_id: null, poster_file: null,
      });
    });

    await waitFor(() => { expect(result.current.isSuccess).toBe(true); });
    const form = post.mock.calls[0]?.[1] as FormData;
    expect(form.get("venue")).toBe("Hall 1");
    expect(form.has("poster_file")).toBe(false);
    expect(form.has("faculty_councillor_id")).toBe(false);
    expect(form.has("kind")).toBe(false);
  });
});

describe("useDownload", () => {
  it("saves the file under the name the server chose", async () => {
    const blob = new Blob(["%PDF"]);
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    vi.spyOn(http, "get").mockResolvedValue({
      data: blob, headers: { "content-disposition": 'attachment; filename="expo.pdf"' },
    });

    const { result } = renderHook(() => useDownload(), { wrapper });
    act(() => { result.current.mutate("/gymkhana/reports/3/file/"); });

    await waitFor(() => { expect(result.current.isSuccess).toBe(true); });
    expect(download.saveBlob).toHaveBeenCalledWith(blob, "expo.pdf");
  });
});
