import { describe, expect, it } from "vitest";
import { getApprovalActionOptions } from "./ElmPage";

describe("getApprovalActionOptions", () => {
  describe("cancellation workflow actions (Fix 1)", () => {
    it("returns final decision actions for CL cancellation at Unit Head review", () => {
      const item = {
        id: 1,
        category: "CL",
        status: "AWAITING_CANCEL",
        employee_id: 10,
        unit_head_id: 20,
        sanction_authority_id: 30,
        recommendation: "",
      };
      expect(getApprovalActionOptions(item)).toEqual([
        "approve_cancellation",
        "reject_cancellation",
      ]);
    });

    it("returns final decision actions for RH cancellation at Unit Head review", () => {
      const item = {
        id: 2,
        category: "RH",
        status: "AWAITING_CANCEL",
        employee_id: 10,
        unit_head_id: 20,
        sanction_authority_id: 30,
        recommendation: "",
      };
      expect(getApprovalActionOptions(item)).toEqual([
        "approve_cancellation",
        "reject_cancellation",
      ]);
    });

    it("returns recommend and not_recommend for EL cancellation before Unit Head recommendation", () => {
      const item = {
        id: 3,
        category: "EL",
        status: "AWAITING_CANCEL",
        employee_id: 10,
        unit_head_id: 20,
        sanction_authority_id: 30,
        recommendation: "",
      };
      expect(getApprovalActionOptions(item)).toEqual([
        "recommend",
        "not_recommend",
      ]);
    });

    it("returns final decision actions for EL cancellation after Unit Head recommendation", () => {
      const itemRecommended = {
        id: 4,
        category: "EL",
        status: "AWAITING_CANCEL",
        employee_id: 10,
        unit_head_id: 20,
        sanction_authority_id: 30,
        recommendation: "RECOMMENDED",
      };
      expect(getApprovalActionOptions(itemRecommended)).toEqual([
        "approve_cancellation",
        "reject_cancellation",
      ]);

      const itemNotRecommended = {
        id: 5,
        category: "EL",
        status: "AWAITING_CANCEL",
        employee_id: 10,
        unit_head_id: 20,
        sanction_authority_id: 30,
        recommendation: "NOT_RECOMMENDED",
      };
      expect(getApprovalActionOptions(itemNotRecommended)).toEqual([
        "approve_cancellation",
        "reject_cancellation",
      ]);
    });

    it("returns final decision actions for other higher-sanction types (COL, VL, SCL) when recommended", () => {
      for (const cat of ["COL", "VL", "SCL"]) {
        expect(
          getApprovalActionOptions({
            category: cat,
            status: "AWAITING_CANCEL",
            recommendation: "",
          })
        ).toEqual(["recommend", "not_recommend"]);

        expect(
          getApprovalActionOptions({
            category: cat,
            status: "AWAITING_CANCEL",
            recommendation: "RECOMMENDED",
          })
        ).toEqual(["approve_cancellation", "reject_cancellation"]);
      }
    });

    it("returns direct final decision actions for Director self-sanction cancellation without recommendation stage", () => {
      const directorItem = {
        id: 6,
        category: "EL",
        status: "AWAITING_CANCEL",
        employee_id: 1,
        unit_head_id: 1,
        sanction_authority_id: 1,
        recommendation: "",
      };
      expect(getApprovalActionOptions(directorItem)).toEqual([
        "approve_cancellation",
        "reject_cancellation",
      ]);
    });
  });

  describe("substitute and regular approval actions", () => {
    it("returns substitute response actions for AWAITING_SUB", () => {
      const item = {
        id: 7,
        category: "CL",
        status: "AWAITING_SUB",
      };
      expect(getApprovalActionOptions(item)).toEqual([
        "accept_substitute",
        "decline_substitute",
      ]);
    });

    it("returns approve and reject for PENDING CL", () => {
      const item = {
        id: 8,
        category: "CL",
        status: "PENDING",
      };
      expect(getApprovalActionOptions(item)).toEqual(["approve", "reject"]);
    });

    it("returns recommend and not_recommend for PENDING EL", () => {
      const item = {
        id: 9,
        category: "EL",
        status: "PENDING",
        employee_id: 10,
        unit_head_id: 20,
        sanction_authority_id: 30,
      };
      expect(getApprovalActionOptions(item)).toEqual(["recommend", "not_recommend"]);
    });

    it("returns approve and reject for RECOMMENDED EL", () => {
      const item = {
        id: 10,
        category: "EL",
        status: "RECOMMENDED",
      };
      expect(getApprovalActionOptions(item)).toEqual(["approve", "reject"]);
    });

    it("returns direct approve and reject for Director self-sanction PENDING EL", () => {
      const directorItem = {
        id: 11,
        category: "EL",
        status: "PENDING",
        employee_id: 1,
        unit_head_id: 1,
        sanction_authority_id: 1,
      };
      expect(getApprovalActionOptions(directorItem)).toEqual(["approve", "reject"]);
    });

    it("returns review_resumption for AWAITING_RESUMPTION status", () => {
      const item = {
        id: 12,
        category: "EL",
        status: "AWAITING_RESUMPTION",
      };
      expect(getApprovalActionOptions(item)).toEqual(["review_resumption"]);
    });

    it("returns empty array for inactive or non-actionable statuses", () => {
      expect(getApprovalActionOptions({ status: "APPROVED" })).toEqual([]);
      expect(getApprovalActionOptions({ status: "CANCELLED" })).toEqual([]);
      expect(getApprovalActionOptions({ status: "WITHDRAWN" })).toEqual([]);
      expect(getApprovalActionOptions({ status: "REJECTED" })).toEqual([]);
    });
  });
});
