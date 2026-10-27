import { describe, expect, it } from "vitest";
import { elmRequestPath } from "./paths";

describe("ELM cursor navigation", () => {
  it("keeps ordinary ELM paths", () => {
    expect(elmRequestPath("applications/?scope=mine")).toBe("/elm/applications/?scope=mine");
  });
  it.each([
    "http://localhost:8000/api/v1/elm/applications/?cursor=abc%3D&scope=mine",
    "/api/v1/elm/applications/?cursor=abc%3D&scope=mine",
    "/elm/applications/?cursor=abc%3D&scope=mine",
  ])("normalizes API pagination links without losing the cursor: %s", (path) => {
    expect(elmRequestPath(path)).toBe("/elm/applications/?cursor=abc%3D&scope=mine");
  });
  it("does not pass a different host to the authenticated HTTP client", () => {
    expect(elmRequestPath("https://other.invalid/api/v1/elm/tasks/?cursor=next"))
      .toBe("/elm/tasks/?cursor=next");
  });
  it.each(["https://other.invalid/private", "/api/v1/placement/applications/"])
    ("rejects links outside the module: %s", (path) => {
      expect(() => elmRequestPath(path)).toThrow("outside Employee Leave Management");
    });
});
