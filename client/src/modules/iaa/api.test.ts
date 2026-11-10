import { describe, expect, it } from "vitest";
import { evidenceLinks, headers, requestActions, type RequestRow } from "./api";

const row: RequestRow = { id: 1, creator_id: 10, kind: "expense", status: "finance_validated",
  department: "CSE", amount: "100.00", description: "Supplies", request_type: "voucher", documents: [],
  assignee_id: 20, assignee_role: "HoD" };

describe("IAA action and role boundaries", () => {
  it("exposes decisions only to the assigned role and identity", () => {
    expect(requestActions(row, "HoD", 20)).toEqual(["approve", "reject"]);
    expect(requestActions(row, "Dean", 20)).toEqual([]);
    expect(requestActions(row, "HoD", 30)).toEqual([]);
  });
  it("never offers self-approval", () => {
    expect(requestActions({ ...row, creator_id: 20 }, "HoD", 20)).toEqual([]);
  });
  it("keeps recorded requests immutable", () => {
    expect(requestActions({ ...row, status: "recorded" }, "Finance Staff", 20)).toEqual([]);
    expect(requestActions({ ...row, status: "recorded" }, "Basic User", 10)).toEqual([]);
  });
  it("keeps System Admin outside operational actions", () => {
    expect(requestActions(row, "System Admin", 20)).toEqual([]);
  });
  it("allows structured responses instead of edits after submission", () => {
    expect(requestActions({ ...row, status: "query_raised" }, "Basic User", 10)).toEqual(["respond"]);
  });
  it("parses evidence links without merging separate documents", () => {
    expect(evidenceLinks("https://example.org/a\r\n\n https://example.org/b "))
      .toEqual(["https://example.org/a", "https://example.org/b"]);
  });
  it("sends the explicitly selected IAA role", () => {
    expect(headers("Auditor")).toEqual({ "X-IAA-Role": "Auditor" });
  });
});
