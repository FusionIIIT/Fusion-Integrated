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
  deptStudent: { username: "stu00002", role: "ug_student", grants: [] },
  deptFaculty: { username: "fac00002", role: "Assistant Professor", grants: [] },
  deptHod: { username: "fac00049", role: "HOD (CSE)", grants: ["HOD (CSE)"] },
  deptAdmin: { username: "stf00019", role: "deptadmin_cse", grants: ["deptadmin_cse"] },
  deptCentral: { username: "stf00002", role: "acadadmin", grants: ["acadadmin"] },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
