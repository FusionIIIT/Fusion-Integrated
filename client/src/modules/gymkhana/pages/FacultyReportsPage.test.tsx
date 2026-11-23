import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { mockHttp, page, pending, refusal, report, show } from "../test/harness";
import FacultyReportsPage from "./FacultyReportsPage";

const PATH = "/gymkhana/reports/";

describe("FacultyReportsPage", () => {
  it("shows a loading state", () => {
    mockHttp({ [PATH]: pending });
    show(<FacultyReportsPage />);
    expect(screen.queryByText("No reports yet")).not.toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockHttp({ [PATH]: page() });
    show(<FacultyReportsPage />);
    expect(await screen.findByText("No reports yet")).toBeInTheDocument();
  });

  it("shows the server's error", async () => {
    mockHttp({ [PATH]: refusal(500, "Database is down") });
    show(<FacultyReportsPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("has nothing to press for a role without the permission", async () => {
    mockHttp({ [PATH]: refusal(403, "no") });
    show(<FacultyReportsPage />);
    expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("opens a report's details and downloads its file", async () => {
    const save = vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    mockHttp({ [PATH]: page(report), "/gymkhana/reports/3/file/": new Blob(["x"]) });
    show(<FacultyReportsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Review Expo" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Meera")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Download report" }));
    await waitFor(() => expect(save).toHaveBeenCalled());
  });
});
