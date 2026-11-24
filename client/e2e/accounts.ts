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
  psAdmin: {
    username: "stf00001", role: "ps_admin", grants: ["ps_admin"],
  },
  psmRequester: {
    username: "fac00001", role: "faculty", grants: ["faculty"],
  },
  psmDirector: {
    username: "stf00002", role: "Director", grants: ["Director"],
  },
  psmDeptAdmin: {
    username: "stf00003", role: "deptadmin_cse", grants: ["deptadmin_cse"],
  },
  psmHod: {
    username: "fac00002", role: "HOD (CSE)", grants: ["HOD (CSE)"],
  },
  psmAccounts: {
    username: "stf00004", role: "Accounts Admin", grants: ["Accounts Admin"],
  },
  psmAuditor: {
    username: "stf00005", role: "Auditor", grants: ["Auditor"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
