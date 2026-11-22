// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

// IAA accounts. Any dump account may hold any invented designation, so these are plain unused
// dump usernames; override them if the dump's differ (`manage.py find_user --kind faculty|staff`).
const iaa = (env: string, fallback: string): string => process.env[env] ?? fallback;

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
  iaaFaculty: { username: iaa("E2E_IAA_FACULTY", "fac00005"), role: "faculty", grants: [] },
  iaaFinance: {
    username: iaa("E2E_IAA_FINANCE", "stf00063"), role: "iaa_finance_staff",
    grants: ["iaa_finance_staff"],
  },
  iaaHod: { username: iaa("E2E_IAA_HOD", "fac00006"), role: "iaa_hod", grants: ["iaa_hod"] },
  iaaAdmin: {
    username: iaa("E2E_IAA_ADMIN", "stf00064"), role: "iaa_system_admin",
    grants: ["iaa_system_admin"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
