import { Button, Card, Container, NumberInput, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePolicy, usePublishPolicy } from "../api/hooks";

export default function PolicyPage() {
  const { data } = usePolicy();
  const publish = usePublishPolicy();

  function save() {
    publish.mutate({
      label: `Replacement of v${data?.version ?? 0}`,
      cl_annual: data?.cl_annual, rh_annual: data?.rh_annual,
      scl_annual: data?.scl_annual, el_staff_annual: data?.el_staff_annual,
      vl_faculty: data?.vl_faculty, col_annual: data?.col_annual,
    }, {
      onSuccess: () => notifications.show({ color: "green", message: "Published" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="sm">
      <PageHeader title="Leave policy" subtitle="Publishing a replacement leaves the previous version unchanged" />
      <Card padding="lg">
        <Stack>
          <Text size="sm" c="dimmed">Effective version {data?.version ?? "none"} — {data?.label}</Text>
          <NumberInput label="CL annual" value={Number(data?.cl_annual ?? 8)} readOnly />
          <NumberInput label="RH annual" value={Number(data?.rh_annual ?? 2)} readOnly />
          <NumberInput label="SCL annual" value={Number(data?.scl_annual ?? 15)} readOnly />
          <NumberInput label="Staff EL annual" value={Number(data?.el_staff_annual ?? 30)} readOnly />
          <NumberInput label="Faculty VL" value={Number(data?.vl_faculty ?? 60)} readOnly />
          <NumberInput label="COL annual" value={Number(data?.col_annual ?? 20)} readOnly />
          <Button onClick={save} loading={publish.isPending}>Publish replacement (same baseline numbers)</Button>
        </Stack>
      </Card>
    </Container>
  );
}
