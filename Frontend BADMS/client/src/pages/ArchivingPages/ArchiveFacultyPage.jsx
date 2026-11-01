import ArchivePanel from "./ArchivePanel";

const COLUMNS = [
  { key: "username", label: "Username" },
  { key: "full_name", label: "Name" },
  { key: "department", label: "Department" },
  { key: "designation", label: "Designation" },
];

const FILTERS = [
  { key: "department", label: "Department" },
  { key: "designation", label: "Designation" },
];

const ArchiveFacultyPage = () => (
  <ArchivePanel
    type="faculty"
    title="Archive Faculty"
    subtitle="Retire departed or retired faculty — archived faculty can no longer log in or be used in any module"
    columns={COLUMNS}
    filterKeys={FILTERS}
  />
);

export default ArchiveFacultyPage;
