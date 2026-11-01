import { FaGraduationCap, FaIdCard, FaUsers } from "react-icons/fa";

export const SECTION_META = {
  Identity: { icon: FaIdCard, color: "blue" },
  Academic: { icon: FaGraduationCap, color: "grape" },
  "Contact & Family": { icon: FaUsers, color: "teal" },
};

export const GENDER_OPTIONS = ["Male", "Female", "Other"];
export const CATEGORY_OPTIONS = ["GEN", "OBC", "SC", "ST", "EWS"];
export const PWD_OPTIONS = ["NO", "YES"];
export const BLOOD_GROUP_OPTIONS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Other"];
export const ADMISSION_MODE_OPTIONS = [
  "JEE Main",
  "JEE Advanced",
  "GATE",
  "DASA",
  "Foreign National",
  "Sponsored",
  "Any other (remarks)",
];
export const INCOME_GROUP_OPTIONS = [
  "Below 1 Lakh",
  "1-2.5 Lakhs",
  "2.5-5 Lakhs",
  "5-8 Lakhs",
  "Above 8 Lakhs",
];
export const PWD_CATEGORY_OPTIONS = [
  "Locomotor Disability",
  "Visual Impairment",
  "Hearing Impairment",
  "Speech and Language Disability",
  "Intellectual Disability",
  "Autism Spectrum Disorder",
  "Multiple Disabilities",
  "Any other (remarks)",
];

export const MANUAL_SECTIONS = [
  {
    title: "Identity",
    fields: [
      { key: "name", label: "Full Name", type: "text", required: true },
      { key: "jeeAppNo", label: "JEE App. No. / CCMT Roll No.", type: "text" },
      { key: "rollNumber", label: "Institute Roll Number", type: "text" },
      { key: "instituteEmail", label: "Institute Email ID", type: "text" },
      { key: "gender", label: "Gender", type: "select", options: GENDER_OPTIONS, required: true },
      { key: "category", label: "Category", type: "select", options: CATEGORY_OPTIONS, required: true },
      { key: "dob", label: "Date of Birth", type: "date" },
      { key: "bloodGroup", label: "Blood Group", type: "select", options: BLOOD_GROUP_OPTIONS },
      { key: "minority", label: "Minority", type: "text" },
      { key: "pwd", label: "PwD", type: "select", options: PWD_OPTIONS, required: true },
      { key: "pwdCategory", label: "PwD Category", type: "select", options: PWD_CATEGORY_OPTIONS, visibleWhen: (v) => v.pwd === "YES" },
    ],
  },
  {
    title: "Academic",
    fields: [
      { key: "branch", label: "Discipline / Branch", type: "discipline", required: true },
      { key: "specialization", label: "Specialization", type: "specialization", specializationOnly: true },
      { key: "jeeRank", label: "AI Rank", type: "number" },
      { key: "categoryRank", label: "Category Rank", type: "number" },
      { key: "allottedCategory", label: "Allotted Category", type: "text" },
      { key: "allottedGender", label: "Allotted Gender", type: "text" },
      { key: "admissionMode", label: "Admission Mode", type: "select", options: ADMISSION_MODE_OPTIONS },
      { key: "incomeGroup", label: "Income Group", type: "select", options: INCOME_GROUP_OPTIONS },
      { key: "income", label: "Annual Income", type: "number" },
    ],
  },
  {
    title: "Contact & Family",
    fields: [
      { key: "phoneNumber", label: "Mobile Number", type: "text" },
      { key: "email", label: "Alternate Email", type: "text" },
      { key: "parentEmail", label: "Parent Email", type: "text" },
      { key: "address", label: "Full Address", type: "textarea", required: true },
      { key: "state", label: "State", type: "text" },
      { key: "country", label: "Country", type: "text" },
      { key: "nationality", label: "Nationality", type: "text" },
      { key: "fname", label: "Father's Name", type: "text", required: true },
      { key: "fatherOccupation", label: "Father's Occupation", type: "text" },
      { key: "fatherMobile", label: "Father Mobile", type: "text" },
      { key: "mname", label: "Mother's Name", type: "text", required: true },
      { key: "motherOccupation", label: "Mother's Occupation", type: "text" },
      { key: "motherMobile", label: "Mother Mobile", type: "text" },
      { key: "aadharNumber", label: "Aadhar Number", type: "text" },
    ],
  },
];

export const EMPTY_MANUAL_FORM = {
  name: "", jeeAppNo: "", rollNumber: "", instituteEmail: "", gender: "", category: "",
  dob: null, bloodGroup: "", minority: "", pwd: "NO", pwdCategory: "",
  branch: "", specialization: "", jeeRank: "", categoryRank: "", allottedCategory: "",
  allottedGender: "", admissionMode: "", incomeGroup: "", income: "",
  phoneNumber: "", email: "", parentEmail: "", address: "", state: "", country: "India",
  nationality: "Indian", fname: "", fatherOccupation: "", fatherMobile: "",
  mname: "", motherOccupation: "", motherMobile: "", aadharNumber: "",
};

export const EXCEL_COLUMNS = [
  "Sno",
  "JEE App. No./CCMT Roll. No.",
  "Institute Roll Number",
  "Name",
  "Discipline",
  "Specialization",
  "Gender",
  "Category",
  "Minority",
  "PWD",
  "PwD Category",
  "PwD Category Remarks",
  "Mobile No",
  "Institute Email ID",
  "Alternate Email ID",
  "Parent Email",
  "Father's Name",
  "Father's Occupation",
  "Father Mobile Number",
  "Mother's Name",
  "Mother's Occupation",
  "Mother Mobile Number",
  "Date of Birth",
  "Blood Group",
  "Blood Group Remarks",
  "Country",
  "Nationality",
  "Admission Mode",
  "Admission Mode Remarks",
  "Income Group",
  "Income",
  "AI rank",
  "Category Rank",
  "allottedcat",
  "Allotted Gender",
  "State",
  "Full Address",
];

export const STATUS_OPTIONS = [
  { value: "NOT_REPORTED", label: "Not Reported" },
  { value: "REPORTED", label: "Reported" },
  { value: "WITHDRAWAL", label: "Withdrawal" },
];

export const STATUS_COLOR = {
  NOT_REPORTED: "gray",
  REPORTED: "green",
  WITHDRAWAL: "red",
};

export const STUDENT_DETAIL_GROUPS = [
  {
    title: "Identity",
    fields: [
      ["Name", "name"],
      ["JEE App. No. / CCMT Roll No.", "jee_app_no"],
      ["Institute Roll Number", "roll_number"],
      ["Institute Email", "institute_email"],
      ["Gender", "gender"],
      ["Category", "category"],
      ["Date of Birth", "date_of_birth"],
      ["Blood Group", "blood_group"],
      ["Minority", "minority"],
      ["PwD", "pwd"],
      ["PwD Category", "pwd_category"],
    ],
  },
  {
    title: "Academic",
    fields: [
      ["Branch", "branch"],
      ["Specialization", "specialization"],
      ["Section", "section"],
      ["AI Rank", "ai_rank"],
      ["Category Rank", "category_rank"],
      ["10th Marks", "tenth_marks"],
      ["12th Marks", "twelfth_marks"],
      ["Allotted Category", "allotted_category"],
      ["Allotted Gender", "allotted_gender"],
      ["Admission Mode", "admission_mode"],
      ["Income Group", "income_group"],
      ["Income", "income"],
      ["Year", "year"],
      ["Academic Year", "academic_year"],
    ],
  },
  {
    title: "Contact & Family",
    fields: [
      ["Mobile", "phone_number"],
      ["Personal Email", "personal_email"],
      ["Parent Email", "parent_email"],
      ["Address", "address"],
      ["State", "state"],
      ["Country", "country"],
      ["Nationality", "nationality"],
      ["Father's Name", "father_name"],
      ["Father's Occupation", "father_occupation"],
      ["Father Mobile", "father_mobile"],
      ["Mother's Name", "mother_name"],
      ["Mother's Occupation", "mother_occupation"],
      ["Mother Mobile", "mother_mobile"],
      ["Aadhar Number", "aadhar_number"],
    ],
  },
];

export const studentToForm = (s) => ({
  name: s.name || "",
  jeeAppNo: s.jee_app_no || "",
  rollNumber: s.roll_number || "",
  instituteEmail: s.institute_email || "",
  gender: s.gender || "",
  category: s.category || "",
  dob: s.date_of_birth ? new Date(s.date_of_birth) : null,
  bloodGroup: s.blood_group || "",
  minority: s.minority || "",
  pwd: s.pwd || "NO",
  pwdCategory: s.pwd_category || "",
  branch: s.branch || "",
  specialization: s.specialization || "",
  jeeRank: s.ai_rank ?? "",
  categoryRank: s.category_rank ?? "",
  allottedCategory: s.allotted_category || "",
  allottedGender: s.allotted_gender || "",
  admissionMode: s.admission_mode || "",
  incomeGroup: s.income_group || "",
  income: s.income ?? "",
  phoneNumber: s.phone_number || "",
  email: s.personal_email || "",
  parentEmail: s.parent_email || "",
  address: s.address || "",
  state: s.state || "",
  country: s.country || "India",
  nationality: s.nationality || "Indian",
  fname: s.father_name || "",
  fatherOccupation: s.father_occupation || "",
  fatherMobile: s.father_mobile || "",
  mname: s.mother_name || "",
  motherOccupation: s.mother_occupation || "",
  motherMobile: s.mother_mobile || "",
  aadharNumber: s.aadhar_number || "",
});

export const ROSTER_COLUMNS = [
  { key: "roll_number", label: "Roll No." },
  { key: "name", label: "Name" },
  { key: "branch", label: "Branch" },
  { key: "specialization", label: "Specialization" },
  { key: "category", label: "Category" },
  { key: "gender", label: "Gender" },
  { key: "institute_email", label: "Institute Email" },
  { key: "status_display", label: "Status" },
];
