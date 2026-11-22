import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, expect, it, vi } from "vitest";

import { http } from "../../lib/http";
import { DepartmentDetailsPage, LabsPage } from "./DetailsPages";
import { FeedbackInboxPage, SubmitFeedbackPage } from "./FeedbackPages";
import NoticesPage from "./NoticesPage";
import { InventoryPage, StockRequestsPage } from "./StockPages";
import TimetablePage from "./TimetablePage";

const access = vi.hoisted(() => ({ permissions: [] as string[] }));
vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({ session: { user: { id: 10 }, active_role: "student" } }),
}));
vi.mock("./DepartmentLayout", () => ({
  useDepartmentCan: () => (permission: string) => access.permissions.includes(permission),
}));
vi.mock("../../lib/http", async (original) => ({
  ...await original<typeof import("../../lib/http")>(),
  http: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));

function show(page: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MantineProvider><QueryClientProvider client={client}>{page}</QueryClientProvider></MantineProvider>);
}

beforeEach(() => {
  vi.mocked(http.get).mockReset();
  vi.mocked(http.post).mockReset().mockResolvedValue({ data: {} });
  access.permissions = [];
  vi.mocked(http.get).mockImplementation(async (url) => ({ data:
    url === "/department/details"
      ? { department: "CSE", official_name: "", general_information: "Office", core_policies: "" }
      : url === "/department/academic-context"
        ? { programme: "", batch_year: null }
        : { results: [], next: null },
  }));
});

const pages = [
  ["inventory", <InventoryPage />, "No inventory items are available."],
  ["requests", <StockRequestsPage />, "No stock requests to show."],
  ["feedback", <FeedbackInboxPage />, "There is no feedback to review."],
  ["labs", <LabsPage />, "There are no lab resource profiles."],
  ["timetable", <TimetablePage />, "There are no applicable timetable slots."],
  ["details", <DepartmentDetailsPage />, "There are no official change proposals."],
  ["notices", <NoticesPage />, "You have no Department notifications."],
] as const;

it.each(pages)("%s shows a loading state", (_name, page) => {
  vi.mocked(http.get).mockImplementation(() => new Promise(() => {}));
  show(page);
  expect(screen.getByLabelText("Loading")).toBeInTheDocument();
});

it.each(pages)("%s shows its empty state", async (_name, page, empty) => {
  show(page);
  expect(await screen.findByText(empty)).toBeInTheDocument();
});

it.each(pages)("%s shows request errors", async (_name, page) => {
  vi.mocked(http.get).mockRejectedValue(new Error("Request failed"));
  show(page);
  expect((await screen.findAllByText("Could not load this")).length).toBeGreaterThan(0);
});

it.each([
  [<InventoryPage />, "Add stock"],
  [<StockRequestsPage />, "Approve"],
  [<FeedbackInboxPage />, "Record review"],
  [<LabsPage />, "Save lab profile"],
  [<TimetablePage />, "Add timetable slot"],
  [<DepartmentDetailsPage />, "Submit for approval"],
] as const)("hides unauthorized write controls (%#)", async (page, button) => {
  show(page);
  await waitFor(() => expect(http.get).toHaveBeenCalled());
  expect(screen.queryByRole("button", { name: button })).not.toBeInTheDocument();
});

it("shows unavailable academic information", async () => {
  show(<TimetablePage />);
  expect(await screen.findByText("No academic programme information is available for your account."))
    .toBeInTheDocument();
});

it("submits feedback and clears the confidential text", async () => {
  show(<SubmitFeedbackPage />);
  expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Feedback", { exact: false }), "Repair the ramp");
  await userEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(await screen.findByText("Feedback submitted.")).toBeInTheDocument();
  expect(http.post).toHaveBeenCalledWith("/department/feedback", { content: "Repair the ramp" });
  expect(screen.getByRole("textbox")).toHaveValue("");
});

it("retains feedback when submission fails", async () => {
  vi.mocked(http.post).mockRejectedValue(new Error("Request failed"));
  show(<SubmitFeedbackPage />);
  await userEvent.type(screen.getByRole("textbox"), "Repair the ramp");
  await userEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(await screen.findByText("Could not load this")).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toHaveValue("Repair the ramp");
});

it("adds stock using the entered quantity", async () => {
  access.permissions = ["department.stock.create"];
  show(<InventoryPage />);
  await userEvent.type(screen.getByLabelText("Item name", { exact: false }), "Cable");
  await userEvent.click(screen.getByRole("button", { name: "Add stock" }));
  await waitFor(() => expect(http.post).toHaveBeenCalledWith("/department/inventory", { name: "Cable", quantity: 1 }));
});

it("saves a lab profile", async () => {
  access.permissions = ["department.lab.update"];
  show(<LabsPage />);
  await userEvent.type(screen.getByLabelText("Lab name", { exact: false }), "Networks");
  await userEvent.type(screen.getByLabelText("Equipment and resource details", { exact: false }), "Ten PCs");
  await userEvent.click(screen.getByRole("button", { name: "Save lab profile" }));
  await waitFor(() => expect(http.post).toHaveBeenCalledWith("/department/labs", { name: "Networks", details: "Ten PCs" }));
});

it("saves general information without changing official fields", async () => {
  access.permissions = ["department.details.update"];
  show(<DepartmentDetailsPage />);
  const input = await screen.findByLabelText("General information");
  await userEvent.clear(input);
  await userEvent.type(input, "Open at nine");
  await userEvent.click(screen.getByRole("button", { name: "Save general information" }));
  await waitFor(() => expect(http.post).toHaveBeenCalledWith("/department/details", { general_information: "Open at nine" }));
});

it("approves a pending stock request with the HOD control", async () => {
  access.permissions = ["department.stock_request.approve"];
  vi.mocked(http.get).mockResolvedValue({ data: { next: null, results: [
    { id: 7, item_name: "Cable", quantity: 1, status: "pending" },
  ] } });
  show(<StockRequestsPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Approve" }));
  await waitFor(() => expect(http.post).toHaveBeenCalledWith("/department/stock-requests/7/action", { action: "approve" }));
  expect(screen.queryByRole("button", { name: "Issue stock" })).not.toBeInTheDocument();
});

it("requires a category before initial feedback review", async () => {
  access.permissions = ["department.feedback.review"];
  vi.mocked(http.get).mockResolvedValue({ data: { next: null, results: [
    { id: 8, content: "Broken ramp", category: "", status: "new" },
  ] } });
  show(<FeedbackInboxPage />);
  expect(await screen.findByRole("button", { name: "Record review" })).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Category", { exact: false }), "Access");
  await userEvent.click(screen.getByRole("button", { name: "Record review" }));
  await waitFor(() => expect(http.post).toHaveBeenCalledWith("/department/feedback/8/action", {
    action: "review", category: "Access", close_simple: false,
  }));
});

it("publishes a timetable slot from the editor", async () => {
  access.permissions = ["department.timetable.update"];
  show(<TimetablePage />);
  await userEvent.click(screen.getByRole("button", { name: "Add timetable slot" }));
  for (const [label, value] of [
    ["Class or lab title", "Algorithms"], ["Term", "Autumn"], ["Programme", "BTech"],
    ["Room", "R1"], ["Start time", "10:00"], ["End time", "11:00"], ["Instructor ID", "42"],
  ] as const) {
    await userEvent.type(screen.getByLabelText(label, { exact: false }), value);
  }
  await userEvent.click(screen.getByRole("button", { name: "Save timetable slot" }));
  await waitFor(() => expect(http.post).toHaveBeenCalledWith("/department/timetable", {
    slots: [expect.objectContaining({ title: "Algorithms", starts_at: "10:00", ends_at: "11:00", instructor_id: 42 })],
  }));
});

it("renders received notices", async () => {
  vi.mocked(http.get).mockResolvedValue({ data: { next: null, results: [
    { id: 9, message: "Stock request #7 was issued.", created_at: "2026-11-22T10:00:00Z" },
  ] } });
  show(<NoticesPage />);
  expect(await screen.findByText("Stock request #7 was issued.")).toBeInTheDocument();
});
