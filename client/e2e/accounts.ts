// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  departmentFaculty: { username: "fac00001", role: "faculty", grants: [] },
  departmentHead: { username: "fac00003", role: "HOD (ME)", grants: ["HOD (ME)"] },
  departmentAdmin: { username: "stf00001", role: "deptadmin_me", grants: ["deptadmin_me"] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
