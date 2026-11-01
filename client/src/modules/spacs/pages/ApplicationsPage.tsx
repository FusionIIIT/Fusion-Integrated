import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useApplications,
  useResubmitApplication,
  useSaveDraft,
  useSubmitApplication,
} from "../api/hooks";
import type { Application } from "../api/types";

function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export default function ApplicationsPage() {
  const applications = useApplications();
  const saveDraft = useSaveDraft();
  const submitApplication = useSubmitApplication();
  const resubmitApplication = useResubmitApplication();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [applicationDataText, setApplicationDataText] = useState("");

  function edit(application: Application) {
    setEditingId(application.public_id);
    setApplicationDataText(
      JSON.stringify(application.application_data, null, 2),
    );
  }

  function save(publicId: string) {
    let value: unknown;
    try {
      value = JSON.parse(applicationDataText);
    } catch {
      notifications.show({
        color: "red",
        title: "Invalid application data",
        message: "Enter valid JSON before saving.",
      });
      return;
    }
    if (!isJsonObject(value)) {
      notifications.show({
        color: "red",
        title: "Invalid application data",
        message: "Application data must be a JSON object.",
      });
      return;
    }

    saveDraft.mutate(
      { public_id: publicId, application_data: value },
      {
        onSuccess: () => {
          setEditingId(null);
          notifications.show({
            color: "green",
            title: "Draft saved",
            message: "Your application changes have been saved.",
          });
        },
        onError: (error) => notifications.show({
          color: "red",
          title: "Could not save draft",
          message: errorMessage(error),
        }),
      },
    );
  }

  function submit(publicId: string, resubmit = false) {
    const mutation = resubmit ? resubmitApplication : submitApplication;
    mutation.mutate(publicId, {
      onSuccess: () => notifications.show({
        color: "green",
        title: resubmit ? "Application resubmitted" : "Application submitted",
        message: "The server recorded the application workflow update.",
      }),
      onError: (error) => notifications.show({
        color: "red",
        title: resubmit ? "Could not resubmit" : "Could not submit",
        message: errorMessage(error),
      }),
    });
  }

  if (applications.error) {
    return <Container size="xl"><ErrorState error={applications.error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Applications"
        subtitle="Your saved drafts and scholarship application status"
      />
      {applications.isPending && <Text c="dimmed">Loading applications…</Text>}
      {!applications.isPending && applications.data?.length === 0 && (
        <Text c="dimmed">You have no applications yet.</Text>
      )}
      <Stack gap="md">
        {(applications.data ?? []).map((application) => {
          const editable = [
            "Not Started / Draft",
            "Correction Required",
          ].includes(application.state);
          const isEditing = editingId === application.public_id;

          return (
            <Card key={application.public_id} withBorder padding="lg">
              <Stack gap="sm">
                <Group justify="space-between">
                  <Text fw={700}>
                    Scholarship application · cycle {application.academic_cycle}
                  </Text>
                  <Badge>{application.state}</Badge>
                </Group>
                <Text size="sm">Application ID: {application.public_id}</Text>
                <Text size="sm">
                  Catalogue version ID: {application.catalogue_version}
                </Text>
                {isEditing && (
                  <>
                    <Textarea
                      label="Application data (JSON object)"
                      minRows={10}
                      autosize
                      value={applicationDataText}
                      onChange={(event) =>
                        setApplicationDataText(event.currentTarget.value)
                      }
                    />
                    <Group>
                      <Button
                        onClick={() => save(application.public_id)}
                        loading={saveDraft.isPending}
                      >
                        Save draft
                      </Button>
                      <Button
                        variant="default"
                        onClick={() => setEditingId(null)}
                      >
                        Cancel
                      </Button>
                    </Group>
                  </>
                )}
                {!isEditing && editable && (
                  <Button variant="default" onClick={() => edit(application)}>
                    Edit draft
                  </Button>
                )}
                {!isEditing && application.state === "Not Started / Draft" && (
                  <Button
                    onClick={() => submit(application.public_id)}
                    loading={submitApplication.isPending}
                  >
                    Submit application
                  </Button>
                )}
                {!isEditing && application.state === "Correction Required" && (
                  <Button
                    onClick={() => submit(application.public_id, true)}
                    loading={resubmitApplication.isPending}
                  >
                    Resubmit application
                  </Button>
                )}
              </Stack>
            </Card>
          );
        })}
      </Stack>
    </Container>
  );
}
