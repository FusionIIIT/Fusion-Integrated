import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Radio, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck, FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRespondVacationSurvey, useVacationSurveys } from "../api/hooks";

export default function SurveyResponsePage() {
  const { data: surveys, isLoading, error } = useVacationSurveys();
  const respond = useRespondVacationSurvey();
  const [selectedResponses, setSelectedResponses] = useState<Record<number, "yes" | "no">>({});

  const handleResponse = (surveyId: number, response: "yes" | "no") => {
    respond.mutate(
      { surveyId, data: { response } },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Response Recorded",
            message: `Recorded '${response.toUpperCase()}' for this vacation survey.`,
          });
          setSelectedResponses((prev) => ({ ...prev, [surveyId]: response }));
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Response Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  };

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const openSurveys = surveys?.filter((s) => s.is_open) || [];

  return (
    <Container size="md">
      <PageHeader title="Vacation Food Continuity Survey" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Respond whether you require mess dining facilities to remain open during upcoming breaks.
        </Text>

        {isLoading ? (
          <Text c="dimmed">Loading surveys...</Text>
        ) : openSurveys.length === 0 ? (
          <Alert color="gray" icon={<FaInfoCircle />}>
            There are no open vacation food continuity surveys at this time.
          </Alert>
        ) : (
          openSurveys.map((survey) => (
            <Card key={survey.id} withBorder padding="md">
              <Stack gap="sm">
                <Group justify="space-between">
                  <Text fw={600} size="lg">
                    {survey.vacation}
                  </Text>
                  <Badge color="green">Open</Badge>
                </Group>
                <Text size="sm" c="dimmed">
                  Response Deadline: {new Date(survey.response_deadline).toLocaleString()}
                </Text>
                <Text size="sm">
                  Will you remain on campus and eat in the mess during this vacation?
                </Text>
                <Group mt="xs">
                  <Button
                    color="teal"
                    variant={selectedResponses[survey.id] === "yes" ? "filled" : "outline"}
                    onClick={() => handleResponse(survey.id, "yes")}
                    loading={respond.isPending}
                  >
                    Yes (I will dine)
                  </Button>
                  <Button
                    color="gray"
                    variant={selectedResponses[survey.id] === "no" ? "filled" : "outline"}
                    onClick={() => handleResponse(survey.id, "no")}
                    loading={respond.isPending}
                  >
                    No (Not needed)
                  </Button>
                </Group>
              </Stack>
            </Card>
          ))
        )}
      </Stack>
    </Container>
  );
}
