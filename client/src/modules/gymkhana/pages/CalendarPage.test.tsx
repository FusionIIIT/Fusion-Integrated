import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import { booking, mockHttp, page, pending, refusal, show } from "../test/harness";
import CalendarPage from "./CalendarPage";

const gets = (over = {}) => ({
  "/gymkhana/venues/": { venues: ["Hall 1", "Hall 2"] }, "/gymkhana/bookings/": page(booking),
  ...over,
});

describe("CalendarPage", () => {
  it("shows a loading state", () => {
    mockHttp(gets({ "/gymkhana/bookings/": pending }));
    show(<CalendarPage />);
    expect(screen.queryByText("No bookings")).not.toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockHttp(gets({ "/gymkhana/bookings/": page() }));
    show(<CalendarPage />);
    expect(await screen.findByText("No bookings")).toBeInTheDocument();
  });

  it("shows the server's error", async () => {
    mockHttp(gets({ "/gymkhana/bookings/": refusal(500, "Database is down") }));
    show(<CalendarPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("offers no poster where there is none", async () => {
    mockHttp(gets({ "/gymkhana/bookings/": page({ ...booking, poster_file: null }) }));
    show(<CalendarPage />);
    expect(await screen.findByText("Expo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /poster/i })).not.toBeInTheDocument();
  });

  it("filters by date", async () => {
    mockHttp(gets());
    show(<CalendarPage />);
    await userEvent.type(await screen.findByLabelText("Date"), "2026-12-10");
    await waitFor(() => expect(http.get).toHaveBeenCalledWith("/gymkhana/bookings/",
      { params: { venue: undefined, booking_date: "2026-12-10" } }));
  });

  it("downloads a poster", async () => {
    const save = vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    mockHttp(gets({ "/gymkhana/bookings/9/poster/": new Blob(["x"]) }));
    show(<CalendarPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Download poster for Expo" }));
    await waitFor(() => expect(save).toHaveBeenCalled());
  });

  it("shows a refused download as the server sent it", async () => {
    mockHttp(gets({ "/gymkhana/bookings/9/poster/": refusal(404, "This file is not available.") }));
    show(<CalendarPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Download poster for Expo" }));
    expect(await screen.findByText("This file is not available.")).toBeInTheDocument();
  });
});
