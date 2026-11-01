import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  TextInput,
  Textarea,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaGraduationCap, FaInfoCircle } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubmitSeminarRequest } from "../api/hooks";

export default function RequestSeminarPage() {
  const navigate = useNavigate();
  const submitMutation = useSubmitSeminarRequest();

  const [topic, setTopic] = useState("");
  const [abstract, setAbstract] = useState("");
  const [programme, setProgramme] = useState("M.Tech");
  const [department, setDepartment] = useState("Computer Science & Engineering");
  const [preferredDate, setPreferredDate] = useState("");
  const [advisorName, setAdvisorName] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) {
      notifications.show({ color: "red", message: "Please provide a seminar topic." });
      return;
    }
    if (!abstract.trim()) {
      notifications.show({ color: "red", message: "Please provide a seminar abstract." });
      return;
    }

    submitMutation.mutate(
      {
        topic: topic.trim(),
        abstract: abstract.trim(),
        programme,
        department,
        preferred_date: preferredDate || null,
        faculty_advisor_name: advisorName.trim(),
      },
      {
        onSuccess: (res) => {
          notifications.show({
            color: "green",
            title: "Request Submitted",
            message: `Seminar request #${res.id} is now Awaiting Scheduling (OA-UC-51).`,
          });
          navigate("/department/my-seminars");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Submission Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Request Graduate Seminar"
        subtitle="Submit a postgraduate seminar scheduling request (OA-UC-51, BW-OAP-09)"
      />

      <Alert icon={<FaInfoCircle />} color="blue" mb="lg">
        Under OA-BR-61, only postgraduate (M.Tech / Ph.D. / M.Des) scholars may schedule graduate seminars.
        Once submitted, your request will be reviewed and scheduled by the Department Administrator.
      </Alert>

      <Card padding="xl" radius="md" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="Seminar Topic / Title"
              placeholder="e.g. Advancements in Deep Reinforcement Learning"
              required
              value={topic}
              onChange={(e) => setTopic(e.currentTarget.value)}
            />

            <Group grow>
              <Select
                label="Academic Programme"
                data={["M.Tech", "Ph.D.", "M.Des", "PG"]}
                value={programme}
                onChange={(val) => setProgramme(val || "M.Tech")}
                required
              />
              <TextInput
                label="Department / Discipline"
                value={department}
                onChange={(e) => setDepartment(e.currentTarget.value)}
              />
            </Group>

            <Group grow>
              <TextInput
                label="Preferred Date (Optional)"
                type="date"
                value={preferredDate}
                onChange={(e) => setPreferredDate(e.currentTarget.value)}
              />
              <TextInput
                label="Thesis Supervisor / Faculty Advisor"
                placeholder="e.g. Dr. A. Sharma"
                value={advisorName}
                onChange={(e) => setAdvisorName(e.currentTarget.value)}
              />
            </Group>

            <Textarea
              label="Seminar Abstract & Summary"
              placeholder="Describe your research motivation, methodology, and key contributions..."
              minRows={5}
              required
              value={abstract}
              onChange={(e) => setAbstract(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/department/my-seminars")}>
                Cancel
              </Button>
              <Button
                type="submit"
                leftSection={<FaGraduationCap />}
                loading={submitMutation.isPending}
              >
                Submit Request
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
