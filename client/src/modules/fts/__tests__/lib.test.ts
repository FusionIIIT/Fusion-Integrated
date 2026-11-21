import { describe, expect, it } from "vitest";

import { ftsErrorMessage } from "../lib/errors";
import { actionsFor } from "../lib/rules";

const file = (over: Partial<Parameters<typeof actionsFor>[0]> = {}) => ({
  status: "in_transit" as const,
  creator_id: "alice",
  current_holder_id: "bob",
  ...over,
});

describe("actionsFor (what the buttons may offer)", () => {
  it("lets the current holder forward, return and archive a circulated file", () => {
    const a = actionsFor(file(), "bob");
    expect(a).toMatchObject({ canForward: true, canReturn: true, canArchive: true });
  });

  it("lets the creator archive a file someone else holds, but not move it", () => {
    const a = actionsFor(file(), "alice");
    expect(a).toMatchObject({ canForward: false, canReturn: false, canArchive: true });
  });

  it("offers nothing to an employee who is neither creator nor holder", () => {
    const a = actionsFor(file(), "carol");
    expect(a).toMatchObject({ canForward: false, canReturn: false, canArchive: false });
  });

  it("lets a draft be sent by its holder but not returned or archived (BR-FTS-005)", () => {
    const a = actionsFor(file({ status: "draft", current_holder_id: "alice" }), "alice");
    expect(a).toMatchObject({ canForward: true, canReturn: false, canArchive: false });
  });

  it("makes an archived file read-only for everyone (BR-FTS-012)", () => {
    const a = actionsFor(file({ status: "archived" }), "bob");
    expect(a).toEqual({
      canForward: false, canReturn: false, canArchive: false, readOnly: true,
    });
  });

  it("offers nothing when the user is unknown", () => {
    expect(actionsFor(file(), undefined)).toMatchObject({
      canForward: false, canReturn: false, canArchive: false,
    });
  });
});

describe("ftsErrorMessage", () => {
  const wrap = (data: unknown) => ({ response: { data } });

  it("reads the FTS view reply {error: text}", () => {
    expect(ftsErrorMessage(wrap({ error: "Archived files are terminal." })))
      .toBe("Archived files are terminal.");
  });

  it("reads DRF field errors", () => {
    expect(ftsErrorMessage(wrap({ comment: ["This field may not be blank."] })))
      .toBe("comment: This field may not be blank.");
  });

  it("names the field in a platform validation envelope", () => {
    expect(ftsErrorMessage(wrap({ error: { message: "bad", details: [
      { field: "receiver_role", message: "This field may not be blank." }] } })))
      .toBe("receiver_role: This field may not be blank.");
  });

  it("reads the platform envelope", () => {
    expect(ftsErrorMessage(wrap({ error: { message: "Not allowed", details: [] } })))
      .toBe("Not allowed");
  });

  it("falls back to a generic message", () => {
    expect(ftsErrorMessage(new Error("network"))).toMatch(/something went wrong/i);
  });

  it("never shows an HTML error page", () => {
    expect(ftsErrorMessage(wrap("<html>500</html>"))).toMatch(/something went wrong/i);
  });
});
