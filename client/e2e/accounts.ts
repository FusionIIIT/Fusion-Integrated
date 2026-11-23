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
  // PHC: one account per role, so no test switches another test's acting role.
  phcStaff: { username: "usr01844", role: "PHC Staff", grants: ["PHC Staff"] },
  phcAccounts: { username: "usr01855", role: "Accounts & Audit", grants: ["Accounts & Audit"] },
  phcAuthority: {
    username: "fac00021", role: "Approving Authority", grants: ["Approving Authority"],
  },
  phcEmployee: { username: "fac00050", role: "faculty", grants: [] },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
