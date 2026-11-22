import { access, boundary, record, resetBoundary, show, unavailable } from "./testSupport";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import AdministrationPage from "./AdministrationPage";
import { PolicyManagement } from "./PolicyManagement";

describe("Administration HTTP capabilities and states", () => {
  beforeEach(resetBoundary);
  it("hides Create from update-only HR and hides Edit from read-only HR", async () => {
    boundary.get.mockResolvedValue({ data: { results: [record] } });
    access.permissions = ["hreis.service_record.update"];
    const update = show(<AdministrationPage />);
    expect(await screen.findByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create employee record" })).toBeNull();
    update.unmount();
    access.permissions = ["hreis.service_record.view"];
    show(<AdministrationPage />);
    await screen.findByText("Professor");
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
  });
  it("distinguishes loading, empty and read failure", async () => {
    boundary.get.mockImplementation(() => new Promise(() => {}));
    const loading = show(<AdministrationPage />);
    expect(screen.getByText("Loading service records...")).toBeInTheDocument();
    loading.unmount();
    boundary.get.mockResolvedValue({ data: { results: [] } });
    const empty = show(<AdministrationPage />);
    expect(await screen.findByText("No employee service records have been created.")).toBeInTheDocument();
    empty.unmount();
    boundary.get.mockRejectedValue(unavailable);
    show(<AdministrationPage />);
    expect(await screen.findByText("Synthetic service unavailable. Retry shortly.")).toBeInTheDocument();
  });
  it("sends only changed fields and invalidates the record query after saving", async () => {
    access.permissions = ["hreis.service_record.update"];
    boundary.get.mockResolvedValue({ data: { results: [record] } });
    show(<AdministrationPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }));
    fireEvent.change(await screen.findByRole("textbox", { name: "Department" }), { target: { value: "ECE" } });
    fireEvent.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() => expect(boundary.patch).toHaveBeenCalledWith("/hreis/service-records/1/",
      { expected_revision: 1, department: "ECE" }, { headers: { "Idempotency-Key": expect.any(String) } }));
    expect(await screen.findByText("Service record saved")).toBeInTheDocument();
    expect(boundary.get.mock.calls.length).toBeGreaterThan(1);
  });
  it("creates an employee through the actual mutation", async () => {
    access.permissions = ["hreis.service_record.create"];
    show(<AdministrationPage />);
    fireEvent.click(screen.getByRole("button", { name: "Create employee record" }));
    fireEvent.change(await screen.findByRole("textbox", { name: "Employee directory ID" }), { target: { value: "10" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Department" }), { target: { value: "CSE" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Designation snapshot" }), { target: { value: "Professor" } });
    fireEvent.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() => expect(boundary.post).toHaveBeenCalledWith("/hreis/service-records/",
      expect.objectContaining({ user_id: 10, department: "CSE", designation_snapshot: "Professor" }), expect.any(Object)));
  });
  it("loads policies, reports empty/errors, and hides publishing without its grant", async () => {
    access.permissions = ["hreis.policy.view"];
    boundary.get.mockImplementation(() => new Promise(() => {}));
    const loading = show(<PolicyManagement />);
    expect(screen.getByText("Loading policy versions...")).toBeInTheDocument();
    loading.unmount();
    boundary.get.mockResolvedValue({ data: { results: [] } });
    const empty = show(<PolicyManagement />);
    expect(await screen.findByText(/No policy versions are configured/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record new policy version" })).toBeNull();
    empty.unmount();
    boundary.get.mockRejectedValue(unavailable);
    show(<PolicyManagement />);
    expect(await screen.findByText(/Could not load the current policy versions: Synthetic/)).toBeInTheDocument();
  });
  it("publishes a policy using the real hook and surfaces a rejected write", async () => {
    access.permissions = ["hreis.policy.view", "hreis.policy.manage"];
    boundary.post.mockRejectedValue(unavailable);
    show(<PolicyManagement />);
    fireEvent.click(screen.getByRole("button", { name: "Record new policy version" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Effective from/ }), { target: { value: "2026-12-01T00:00:00Z" } });
    fireEvent.click(screen.getByRole("button", { name: "Record immutable policy version" }));
    expect(await screen.findByText("Synthetic service unavailable. Retry shortly.")).toBeInTheDocument();
    expect(boundary.post).toHaveBeenCalledWith("/hreis/policies/", {
      family: "leave", version: 1, effective_from: "2026-12-01T00:00:00.000Z", effective_until: null, parameters: {},
    }, expect.any(Object));
  });
});
