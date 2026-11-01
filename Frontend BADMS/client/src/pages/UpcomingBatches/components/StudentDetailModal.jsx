/* eslint-disable react/prop-types */
import { Avatar, Badge, Box, Card, CloseButton, Group, Modal, SimpleGrid, Stack, Text, ThemeIcon } from "@mantine/core";
import { FaGraduationCap, FaIdCard, FaPhoneAlt, FaUsers } from "react-icons/fa";
import { STATUS_COLOR } from "../config/studentFields";

const GROUPS = [
  {
    title: "Identity & Personal",
    icon: FaIdCard,
    color: "blue",
    fields: [
      ["JEE App. / CCMT No.", "jee_app_no"],
      ["Gender", "gender"],
      ["Category", "category"],
      ["Date of Birth", "date_of_birth"],
      ["Blood Group", "blood_group"],
      ["Minority", "minority"],
      ["PwD", "pwd"],
      ["PwD Category", "pwd_category"],
      ["Aadhar Number", "aadhar_number"],
    ],
  },
  {
    title: "Academic",
    icon: FaGraduationCap,
    color: "grape",
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
      ["Annual Income", "income"],
      ["Academic Year", "academic_year"],
    ],
  },
  {
    title: "Contact",
    icon: FaPhoneAlt,
    color: "teal",
    fields: [
      ["Mobile", "phone_number"],
      ["Personal Email", "personal_email"],
      ["Parent Email", "parent_email"],
      ["Address", "address"],
      ["State", "state"],
      ["Country", "country"],
      ["Nationality", "nationality"],
    ],
  },
  {
    title: "Family",
    icon: FaUsers,
    color: "orange",
    fields: [
      ["Father's Name", "father_name"],
      ["Father's Occupation", "father_occupation"],
      ["Father Mobile", "father_mobile"],
      ["Mother's Name", "mother_name"],
      ["Mother's Occupation", "mother_occupation"],
      ["Mother Mobile", "mother_mobile"],
    ],
  },
];

const initials = (name) =>
  (name || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase() || "?";

const isEmpty = (v) => v === null || v === undefined || v === "";

const Field = ({ label, value }) => (
  <Box>
    <Text c="dimmed" fw={600} tt="uppercase" style={{ fontSize: "0.66rem", letterSpacing: "0.04em" }}>
      {label}
    </Text>
    <Text size="sm" fw={500} c={isEmpty(value) ? "dimmed" : undefined} style={{ wordBreak: "break-word" }}>
      {isEmpty(value) ? "—" : String(value)}
    </Text>
  </Box>
);

const StudentDetailModal = ({ opened, onClose, student }) => {
  if (!student) return null;

  const chips = [
    student.roll_number,
    student.section ? `Section ${student.section}` : null,
    student.category,
    student.admission_mode,
  ].filter(Boolean);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      radius="md"
      padding={0}
      withCloseButton={false}
      overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
    >
      <Box
        p="lg"
        style={{
          background: "linear-gradient(135deg, var(--mantine-color-blue-7), var(--mantine-color-indigo-9))",
          color: "white",
        }}
      >
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Group wrap="nowrap" gap="md">
            <Avatar
              size={58}
              radius="md"
              styles={{
                placeholder: { backgroundColor: "rgba(255,255,255,0.2)", color: "white", fontWeight: 700, fontSize: "1.1rem" },
              }}
            >
              {initials(student.name)}
            </Avatar>
            <div>
              <Group gap="xs" align="center">
                <Text fw={700} size="xl" c="white">
                  {student.name}
                </Text>
                <Badge color={STATUS_COLOR[student.reported_status] || "gray"} variant="white">
                  {student.status_display}
                </Badge>
              </Group>
              <Text size="sm" c="rgba(255,255,255,0.8)">
                {student.institute_email || "No institute email"}
              </Text>
              <Group gap={6} mt={8}>
                {chips.map((c) => (
                  <Badge key={c} variant="white" color="gray" size="sm" radius="sm" style={{ textTransform: "none" }}>
                    {c}
                  </Badge>
                ))}
              </Group>
            </div>
          </Group>
          <CloseButton onClick={onClose} size="lg" c="white" variant="transparent" aria-label="Close" />
        </Group>
      </Box>

      <Stack gap="md" p="lg">
        {GROUPS.map((group) => (
          <Card key={group.title} withBorder radius="md" padding="md">
            <Group gap="xs" mb="sm">
              <ThemeIcon variant="light" color={group.color} size="md" radius="sm">
                <group.icon size={13} />
              </ThemeIcon>
              <Text fw={600} size="sm">
                {group.title}
              </Text>
            </Group>
            <SimpleGrid cols={{ base: 1, xs: 2, md: 3 }} spacing="lg" verticalSpacing="sm">
              {group.fields.map(([label, key]) => (
                <Field key={key} label={label} value={student[key]} />
              ))}
            </SimpleGrid>
          </Card>
        ))}
      </Stack>
    </Modal>
  );
};

export default StudentDetailModal;
