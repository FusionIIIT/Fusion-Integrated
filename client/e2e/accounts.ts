// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
  // PHC: one staff account holds the three claim offices; nobody may act on their own claim.
  phcStaff: { username: "stf00062", role: "PHC Staff", grants: ["PHC Staff"] },
  phcAccounts: { username: "stf00062", role: "Accounts & Audit", grants: ["Accounts & Audit"] },
  phcAuthority: {
    username: "stf00062", role: "Approving Authority", grants: ["Approving Authority"],
  },
  phcEmployee: { username: "fac00005", role: "faculty", grants: [] },
  // Decides requisitions, which the PHC Staff account raises.
  phcRequisitionAuthority: {
    username: "fac00005", role: "Approving Authority", grants: ["Approving Authority"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
