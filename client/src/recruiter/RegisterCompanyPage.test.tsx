/** A company's own registration request (PC-UC-014). */
import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegisterCompanyPage from "./RegisterCompanyPage";

const api = vi.hoisted(() => ({ useRegisterMyCompany: vi.fn() }));
vi.mock("./api", () => api);

const mutate = vi.fn();

function page() {
  return render(<MantineProvider><RegisterCompanyPage /></MantineProvider>);
}

describe("RegisterCompanyPage", () => {
  beforeEach(() => {
    mutate.mockReset();
    api.useRegisterMyCompany.mockReturnValue(
      { mutate, isPending: false, isSuccess: false, isError: false });
  });

  it("submits only once the name and contact are given", () => {
    page();
    const submit = screen.getByRole("button", { name: "Submit registration" });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Company name/), { target: { value: "Acme" } });
    fireEvent.change(screen.getByLabelText(/Contact person/), { target: { value: "R" } });
    fireEvent.change(screen.getByLabelText(/Contact email/),
      { target: { value: "hr@acme.test" } });
    fireEvent.click(submit);
    expect(mutate).toHaveBeenCalledWith(expect.objectContaining(
      { name: "Acme", contact_email: "hr@acme.test" }));
  });

  it("confirms a recorded request", () => {
    api.useRegisterMyCompany.mockReturnValue({
      mutate, isPending: false, isSuccess: true, isError: false,
      data: { detail: "Registration received." } });
    page();
    expect(screen.getByText("Registration received.")).toBeInTheDocument();
  });

  it("shows the server's refusal", () => {
    api.useRegisterMyCompany.mockReturnValue({
      mutate, isPending: false, isSuccess: false, isError: true,
      error: new Error("Too many requests") });
    page();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
