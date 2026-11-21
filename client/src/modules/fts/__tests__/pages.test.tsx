import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreateFilePage from "../pages/CreateFilePage";
import FileDetailPage from "../pages/FileDetailPage";
import InboxPage from "../pages/InboxPage";

const { get, post, auth } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  auth: { username: "bob", role: "Faculty" },
}));

vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()),
  http: { get, post },
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    session: { user: { username: auth.username }, active_role: auth.role },
  }),
}));

const summary = {
  id: 5, uin: "FTS-2026-0005", subject: "Lab purchase", priority: "high",
  category: "finance", status: "in_transit", creator_id: "alice",
  current_holder_id: "bob", updated_at: "2026-11-01T10:00:00Z",
};

const detail = {
  id: 5, uin: "FTS-2026-0005", subject: "Lab purchase", description: "Quotes attached",
  priority: "high", category: "finance", status: "in_transit",
  creator_id: "alice", creator_role: "Faculty", current_holder_id: "bob",
  current_holder_role: "Staff", is_draft: false,
  created_at: "2026-10-30T09:00:00Z", updated_at: "2026-11-01T10:00:00Z",
};

const history = [
  { movement_id: 1, action: "created", from_user_id: "alice", from_role: "Faculty",
    to_user_id: "alice", to_role: "Faculty", created_at: "2026-10-30T09:00:00Z",
    comments: [{ author_id: "alice", author_role: "Faculty",
                 remarks: "Please purchase the equipment.", created_at: null }] },
  { movement_id: 2, action: "forwarded", from_user_id: "alice", from_role: "Faculty",
    to_user_id: "bob", to_role: "Staff", created_at: "2026-10-31T09:00:00Z",
    comments: [{ author_id: "alice", author_role: "Faculty",
                 remarks: "For your approval.", created_at: null }] },
];

function serve(file: object = detail) {
  get.mockImplementation(async (url: string) => {
    if (url.endsWith("/history/")) return { data: history };
    if (/\/fts\/files\/\d+\/$/.test(url)) return { data: file };
    if (url.endsWith("/inbox/")) return { data: [summary] };
    return { data: [] };
  });
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}
                      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/fts/inbox" element={<InboxPage />} />
            <Route path="/fts/new" element={<CreateFilePage />} />
            <Route path="/fts/files/:id" element={<FileDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

beforeEach(() => {
  auth.username = "bob";
  auth.role = "Faculty";
  get.mockReset();
  post.mockReset();
});

describe("Inbox (FTS-UC-005)", () => {
  it("lists the files returned by /fts/files/inbox/", async () => {
    serve();
    renderAt("/fts/inbox");
    expect(await screen.findByText("FTS-2026-0005")).toBeInTheDocument();
    expect(screen.getByText("Lab purchase")).toBeInTheDocument();
    expect(screen.getByText("In transit")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/fts/files/inbox/");
  });

  it("shows an explicit empty state", async () => {
    get.mockResolvedValue({ data: [] });
    renderAt("/fts/inbox");
    expect(await screen.findByText("Your inbox is empty")).toBeInTheDocument();
  });

  it("shows the server's error text", async () => {
    get.mockRejectedValue({ response: { data: { error: "Inbox unavailable" } } });
    renderAt("/fts/inbox");
    expect(await screen.findByText("Inbox unavailable")).toBeInTheDocument();
  });
});

describe("Create file (FTS-UC-001)", () => {
  it("blocks save without a subject or an initial comment (BR-FTS-004)", async () => {
    const user = userEvent.setup();
    renderAt("/fts/new");

    await user.click(screen.getByRole("button", { name: "Save draft" }));
    expect(screen.getByText("A subject is required.")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Subject/), "Leave policy");
    await user.click(screen.getByRole("button", { name: "Save draft" }));
    expect(screen.getByText("An initial comment is required.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("posts the backend's create-draft payload and opens the new file", async () => {
    serve();
    post.mockResolvedValue({ data: { file_id: 5, uin: "FTS-2026-0005",
      subject: "Leave policy", status: "draft", is_draft: true } });
    const user = userEvent.setup();
    renderAt("/fts/new");

    await user.type(screen.getByLabelText(/Subject/), "Leave policy");
    await user.type(screen.getByLabelText(/Initial comment/), "Please review.");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/fts/files/create-draft/",
      {
        subject: "Leave policy", initial_comment: "Please review.",
        description: "", priority: "medium", category: "general",
        creator_role: "Faculty",
      },
    ));
    expect(await screen.findByText("File no. FTS-2026-0005")).toBeInTheDocument();
  });
});

describe("File detail (FTS-UC-005/006)", () => {
  it("shows the file, its initial comment and the chronological history", async () => {
    serve();
    renderAt("/fts/files/5");
    expect(await screen.findByText("Lab purchase")).toBeInTheDocument();
    expect(screen.getAllByText("Please purchase the equipment.").length).toBeGreaterThan(0);
    expect(await screen.findByText("For your approval.")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/fts/files/5/history/");
  });

  it("offers Forward, Return and Archive to the current holder", async () => {
    serve();
    renderAt("/fts/files/5");
    expect(await screen.findByRole("button", { name: "Forward" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Return" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
  });

  it("offers nothing to someone who neither holds nor created the file", async () => {
    auth.username = "carol";
    serve();
    renderAt("/fts/files/5");
    await screen.findByText("Lab purchase");
    expect(screen.queryByRole("button", { name: "Forward" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Return" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Archive" })).toBeNull();
  });

  it("presents an archived file as read-only with no actions (BR-FTS-012)", async () => {
    serve({ ...detail, status: "archived" });
    renderAt("/fts/files/5");
    expect(await screen.findByText("Read-only")).toBeInTheDocument();
    expect(screen.getByText(/cannot be changed or forwarded/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Forward" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Archive" })).toBeNull();
  });

  it("lets the creator send a draft but not return or archive it", async () => {
    auth.username = "alice";
    serve({ ...detail, status: "draft", is_draft: true, current_holder_id: "alice" });
    renderAt("/fts/files/5");
    expect(await screen.findByRole("button", { name: "Send" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Return" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Archive" })).toBeNull();
  });
});

describe("Movement actions", () => {
  it("forward needs a recipient and a comment, then posts the backend payload", async () => {
    serve();
    post.mockResolvedValue({ data: { file_id: 5, new_status: "in_transit", movement_id: 9 } });
    const user = userEvent.setup();
    renderAt("/fts/files/5");

    await user.click(await screen.findByRole("button", { name: "Forward" }));
    const send = await screen.findByRole("button", { name: "Send" });
    expect(send).toBeDisabled();
    expect(screen.getByText("A movement comment is required.")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Movement comment/), "Please approve.");
    expect(send).toBeDisabled();
    expect(screen.getByText("Choose who to send the file to.")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Send to/), "carol");
    expect(send).toBeEnabled();
    await user.click(send);

    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/fts/files/5/forward/",
      { receiver_id: "carol", comment: "Please approve.", sender_role: "Faculty" },
    ));
  });

  it("shows the server's refusal inside the dialog", async () => {
    serve();
    post.mockRejectedValue({ response: { status: 400, data: {
      error: "Only the current custodian can forward this file (BR-FTS-001)." } } });
    const user = userEvent.setup();
    renderAt("/fts/files/5");

    await user.click(await screen.findByRole("button", { name: "Forward" }));
    await user.type(await screen.findByLabelText(/Send to/), "carol");
    await user.type(screen.getByLabelText(/Movement comment/), "Go ahead.");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(/Only the current custodian/)).toBeInTheDocument();
  });

  it("return posts to return_file_action with a mandatory comment (BR-FTS-006)", async () => {
    serve();
    post.mockResolvedValue({ data: { file_id: 5, new_status: "returned", movement_id: 10 } });
    const user = userEvent.setup();
    renderAt("/fts/files/5");

    await user.click(await screen.findByRole("button", { name: "Return" }));
    const submit = await within(await screen.findByRole("dialog"))
      .findByRole("button", { name: "Return" });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText(/Movement comment/), "Needs a quote.");
    await user.click(submit);

    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/fts/files/5/return_file_action/",
      { comment: "Needs a quote.", sender_role: "Faculty" },
    ));
  });

  it("archive needs closing remarks and posts them with the role", async () => {
    serve();
    post.mockResolvedValue({ data: { file_id: 5, status: "archived", archived_by: "bob" } });
    const user = userEvent.setup();
    renderAt("/fts/files/5");

    await user.click(await screen.findByRole("button", { name: "Archive" }));
    const dialog = await screen.findByRole("dialog");
    const confirm = within(dialog).getByRole("button", { name: "Archive" });
    expect(confirm).toBeDisabled();

    await user.type(within(dialog).getByLabelText(/Closing remarks/), "Done.");
    await user.click(confirm);

    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/fts/files/5/archive/", { remarks: "Done.", user_role: "Faculty" },
    ));
  });
});
