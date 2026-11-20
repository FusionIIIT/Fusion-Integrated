import { FaBriefcase, FaCircle, FaClipboardList } from "react-icons/fa";
import { describe, expect, it } from "vitest";

import { resolveIcon } from "./icons";

describe("resolveIcon", () => {
  it("draws a Phosphor name from a module registry as its Font Awesome twin", () => {
    expect(resolveIcon("Briefcase")).toBe(FaBriefcase);
    expect(resolveIcon("ClipboardText")).toBe(FaClipboardList);
  });

  it("keeps Font Awesome names and falls back to a circle for unknown ones", () => {
    expect(resolveIcon("FaBriefcase")).toBe(FaBriefcase);
    expect(resolveIcon("NoSuchIcon")).toBe(FaCircle);
    expect(resolveIcon(undefined)).toBe(FaCircle);
  });
});
