import { useEffect, useState } from "react";
import {
  Alert, Button, Card, Container, Group, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaFileAlt, FaSave } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useGenerateResume, useMyPlacementProfile, useSavePlacementProfile,
  type PlacementProfile,
} from "../api/hooks";

const emptyProfile: PlacementProfile = {
  summary: "", skills: [], achievements: [], certifications: [],
  projects: [], links: [], updated_at: null,
};
const lines = (values: string[]) => values.join("\n");
const textLines = (value: string) => value.split("\n").map((x) => x.trim())
  .filter(Boolean);
const entries = (value: string, fields: string[]): Record<string, string>[] => textLines(value).map((line) => {
  const parts = line.split("|").map((x) => x.trim());
  return Object.fromEntries(fields.map((field, index) => [field, parts[index] ?? ""]));
});

export default function PlacementProfilePage() {
  const query = useMyPlacementProfile();
  const save = useSavePlacementProfile();
  const generate = useGenerateResume();
  const [summary, setSummary] = useState("");
  const [skills, setSkills] = useState("");
  const [projects, setProjects] = useState("");
  const [achievements, setAchievements] = useState("");
  const [certifications, setCertifications] = useState("");
  const [links, setLinks] = useState("");

  useEffect(() => {
    const profile = query.data ?? emptyProfile;
    setSummary(profile.summary);
    setSkills(lines(profile.skills));
    setProjects(profile.projects.map((p) =>
      [p.title, p.description ?? "", (p.technologies ?? []).join(", "), p.url ?? ""]
        .join(" | ")).join("\n"));
    setAchievements(profile.achievements.map((a) =>
      [a.title, a.description ?? "", a.date ?? ""].join(" | ")).join("\n"));
    setCertifications(profile.certifications.map((c) =>
      [c.name, c.issuer ?? "", c.issued_on ?? "", c.credential_url ?? ""]
        .join(" | ")).join("\n"));
    setLinks(profile.links.map((link) => `${link.label} | ${link.url}`).join("\n"));
  }, [query.data]);

  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;

  function saveProfile() {
    save.mutate({
      summary,
      skills: textLines(skills),
      projects: entries(projects, ["title", "description", "technology_text", "url"])
        .map((p) => ({
          title: p.title,
          description: p.description,
          technologies: p.technology_text.split(",").map((x) => x.trim()).filter(Boolean),
          url: p.url,
        })),
      achievements: entries(achievements, ["title", "description", "date"])
        .map((a) => ({ title: a.title, description: a.description, date: a.date })),
      certifications: entries(certifications,
        ["name", "issuer", "issued_on", "credential_url"]).map((c) => ({
          name: c.name, issuer: c.issuer, issued_on: c.issued_on,
          credential_url: c.credential_url,
        })),
      links: entries(links, ["label", "url"])
        .map((link) => ({ label: link.label, url: link.url })),
    }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Profile saved", message: "Your placement profile was updated.",
      }),
      onError: (error) => notifications.show({
        color: "red", title: "Could not save profile", message: errorMessage(error),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader title="Placement Profile"
        subtitle="Maintain the skills and experience used in your placement resume" />
      <Stack>
        <Alert color="blue" title="Academic records">
          Academic details are read from Fusion's academic system and cannot be edited here.
        </Alert>
        <Card withBorder padding="lg">
          <Stack>
            <Textarea label="Profile summary" minRows={3} maxLength={2000}
              value={summary} onChange={(event) => setSummary(event.currentTarget.value)} />
            <Textarea label="Skills" description="One skill per line" minRows={3}
              value={skills} onChange={(event) => setSkills(event.currentTarget.value)} />
            <Textarea label="Projects" description="One per line: title | description | technologies (comma separated) | URL"
              minRows={4} value={projects}
              onChange={(event) => setProjects(event.currentTarget.value)} />
            <Textarea label="Achievements" description="One per line: title | description | date"
              minRows={3} value={achievements}
              onChange={(event) => setAchievements(event.currentTarget.value)} />
            <Textarea label="Certifications" description="One per line: name | issuer | date | credential URL"
              minRows={3} value={certifications}
              onChange={(event) => setCertifications(event.currentTarget.value)} />
            <Textarea label="Professional links" description="One per line: label | URL"
              minRows={2} value={links}
              onChange={(event) => setLinks(event.currentTarget.value)} />
            <Group justify="flex-end">
              <Button leftSection={<FaSave />} loading={save.isPending}
                onClick={saveProfile}>Save profile</Button>
            </Group>
          </Stack>
        </Card>
        <Card withBorder padding="lg">
          <Stack>
            <Group justify="space-between">
              <Text fw={600}>Structured resume</Text>
              <Button variant="light" leftSection={<FaFileAlt />}
                loading={generate.isPending}
                onClick={() => generate.mutate(undefined, {
                  onError: (error) => notifications.show({
                    color: "red", title: "Resume unavailable", message: errorMessage(error),
                  }),
                })}>Generate resume</Button>
            </Group>
            {generate.data && <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              {JSON.stringify(generate.data, null, 2)}
            </pre>}
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
