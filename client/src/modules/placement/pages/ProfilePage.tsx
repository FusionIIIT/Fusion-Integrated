import { useEffect, useState } from "react";
import {
  Alert, Button, Card, Container, Grid, Group, List, Progress, Stack, TagsInput,
  Text, Textarea, TextInput, ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaExclamationCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DocumentsCard } from "../components/DocumentsCard";
import { useMyProfile, useSaveProfile } from "../api/hooks";

export default function ProfilePage() {
  const { data, isPending, error } = useMyProfile();
  const save = useSaveProfile();

  const [form, setForm] = useState({
    headline: "", about: "", phone: "", alternate_email: "",
    github_url: "", linkedin_url: "", portfolio_url: "",
  });
  const [skills, setSkills] = useState<string[]>([]);
  const [achievements, setAchievements] = useState<string[]>([]);
  const [certifications, setCertifications] = useState<string[]>([]);

  // Seeded outside render so a background refetch cannot clobber typing.
  useEffect(() => {
    if (!data || data.exists === false) return;
    setForm({
      headline: data.headline ?? "", about: data.about ?? "",
      phone: data.phone ?? "", alternate_email: data.alternate_email ?? "",
      github_url: data.github_url ?? "", linkedin_url: data.linkedin_url ?? "",
      portfolio_url: data.portfolio_url ?? "",
    });
    setSkills(data.skills ?? []);
    setAchievements(data.achievements ?? []);
    setCertifications(data.certifications ?? []);
  }, [data]);

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const percent = data?.completeness_percent ?? 0;
  const complete = data?.is_complete ?? false;
  const missing = data?.missing_fields ?? [];

  function submit() {
    save.mutate(
      { ...form, skills, achievements, certifications },
      {
        onSuccess: () => notifications.show({
          color: "green", title: "Profile saved",
          message: "Your placement profile has been updated.",
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not save", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="My Profile"
        subtitle="Used for eligibility checks and your generated resume"
        action={
          <Button onClick={submit} loading={save.isPending} disabled={isPending}>
            Save profile
          </Button>
        }
      />

      <Card padding="lg" mb="md">
        <Group justify="space-between" mb={6}>
          <Text fw={600}>Profile completeness</Text>
          <Text fw={700} c={complete ? "teal" : "orange"}>{percent}%</Text>
        </Group>
        <Progress value={percent} color={complete ? "teal" : "orange"} size="lg" />

        {complete ? (
          <Alert mt="md" variant="light" color="green" icon={<FaCheckCircle />}>
            <Text size="sm">Your profile is complete. You can apply to postings.</Text>
          </Alert>
        ) : (
          <Alert
            mt="md" variant="light" color="orange"
            icon={<FaExclamationCircle />}
            title="Complete your profile before applying"
          >
            {/* Named fields, not a bare percentage — a student blocked from
                applying should be told exactly what to fill in. */}
            <List
              size="sm" spacing={4} mt={4}
              icon={
                <ThemeIcon size={14} radius="xl" color="orange" variant="light">
                  <FaExclamationCircle size={8} />
                </ThemeIcon>
              }
            >
              {missing.map((m) => <List.Item key={m.field}>{m.label}</List.Item>)}
            </List>
          </Alert>
        )}
      </Card>

      <DocumentsCard />

      <Card padding="lg">
        <Stack gap="md">
          <TextInput
            label="Headline" value={form.headline}
            onChange={(e) => setForm({ ...form, headline: e.currentTarget.value })}
            placeholder="Final-year CSE student · backend and distributed systems"
          />
          <Textarea
            label="About" autosize minRows={4} value={form.about}
            onChange={(e) => setForm({ ...form, about: e.currentTarget.value })}
          />
          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="Phone" value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.currentTarget.value })}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="Alternate email" value={form.alternate_email}
                onChange={(e) =>
                  setForm({ ...form, alternate_email: e.currentTarget.value })}
              />
            </Grid.Col>
          </Grid>

          <TagsInput
            label="Skills" value={skills} onChange={setSkills}
            description="Matched against a posting's required skills"
            placeholder="Add a skill and press Enter"
          />
          <TagsInput
            label="Achievements" value={achievements} onChange={setAchievements}
          />
          <TagsInput
            label="Certifications" value={certifications}
            onChange={setCertifications}
          />

          <Grid>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput
                label="GitHub" value={form.github_url}
                onChange={(e) =>
                  setForm({ ...form, github_url: e.currentTarget.value })}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput
                label="LinkedIn" value={form.linkedin_url}
                onChange={(e) =>
                  setForm({ ...form, linkedin_url: e.currentTarget.value })}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput
                label="Portfolio" value={form.portfolio_url}
                onChange={(e) =>
                  setForm({ ...form, portfolio_url: e.currentTarget.value })}
              />
            </Grid.Col>
          </Grid>

          <Alert variant="light" color="gray">
            <Text size="sm">
              Your CPI, credits and backlogs are not editable here. They come
              from your last declared academic result and are read directly from
              the institute&apos;s records.
            </Text>
          </Alert>
        </Stack>
      </Card>
    </Container>
  );
}
