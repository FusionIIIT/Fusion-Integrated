import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaFileSignature } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { PlacementRecordCard } from "../components/PlacementRecordCard";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useOffers, useRespondToOffer } from "../api/hooks";
import type { Offer } from "../api/types";

function remaining(iso: string): { text: string; urgent: boolean; over: boolean } {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return { text: "deadline passed", urgent: true, over: true };
  const hours = Math.floor(ms / 3_600_000);
  if (hours < 24) {
    return { text: `${hours}h ${Math.floor((ms % 3_600_000) / 60_000)}m left`,
      urgent: true, over: false };
  }
  return { text: `${Math.floor(hours / 24)} days left`, urgent: hours < 72,
    over: false };
}

export default function OffersPage() {
  const { data, isPending, error } = useOffers();
  const respond = useRespondToOffer();
  const [confirm, setConfirm] = useState<
    { offer: Offer; accept: boolean } | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const offers = data?.results ?? [];
  const live = offers.filter((o) => o.status === "issued");
  const past = offers.filter((o) => o.status !== "issued");

  function act() {
    if (!confirm) return;
    respond.mutate(
      { id: confirm.offer.id, accept: confirm.accept },
      {
        onSuccess: () => {
          notifications.show({
            color: confirm.accept ? "green" : "gray",
            title: confirm.accept ? "Offer accepted" : "Offer declined",
            message: confirm.accept
              ? "Your placement has been recorded."
              : "The offer has been declined.",
          });
          setConfirm(null);
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record your response",
          message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="My Offers"
        subtitle="Offers extended to you, and the deadline to answer each one"
      />

      {/* Post-acceptance obligations (rules 22 and 24). Renders nothing until
          there is a placement on record. */}
      <PlacementRecordCard />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && offers.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaFileSignature size={26} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No offers yet</Text>
            <Text size="sm" c="dimmed">
              Offers extended to you will appear here with a response deadline.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {live.map((o) => {
          const left = remaining(o.respond_by);
          return (
            <Card key={o.id} padding="lg" withBorder>
              <Group justify="space-between" align="flex-start" wrap="wrap">
                <Stack gap={4}>
                  <Group gap="xs">
                    <Text fw={700} size="lg">{o.posting?.title}</Text>
                    {o.is_dream && (
                      <Badge color="grape" variant="light">dream offer</Badge>
                    )}
                  </Group>
                  <Text c="dimmed" size="sm">{o.posting?.company?.name}</Text>
                  <Group gap="lg" mt={4}>
                    <Text size="sm"><b>CTC</b> {o.ctc_lpa ?? "—"} LPA</Text>
                    <Text size="sm">
                      <b>Respond by</b> {new Date(o.respond_by).toLocaleString()}
                    </Text>
                  </Group>
                </Stack>
                <Stack gap="xs" align="flex-end">
                  <Badge color={left.urgent ? "red" : "blue"} variant="light">
                    {left.text}
                  </Badge>
                  <Group gap="xs">
                    <Button
                      variant="default"
                      onClick={() => setConfirm({ offer: o, accept: false })}
                      disabled={left.over}
                    >
                      Decline
                    </Button>
                    <Button
                      onClick={() => setConfirm({ offer: o, accept: true })}
                      disabled={left.over}
                    >
                      Accept
                    </Button>
                  </Group>
                </Stack>
              </Group>

              {left.over && (
                <Alert
                  mt="md" variant="light" color="red"
                  icon={<FaExclamationTriangle />}
                >
                  <Text size="sm">
                    The deadline has passed. This offer will be marked expired.
                    Contact the placement office if you believe this is wrong.
                  </Text>
                </Alert>
              )}
            </Card>
          );
        })}

        {past.length > 0 && (
          <Card padding="lg">
            <Text fw={600} mb="sm">Past offers</Text>
            <Stack gap="sm">
              {past.map((o) => (
                <Group key={o.id} justify="space-between">
                  <Stack gap={0}>
                    <Text size="sm" fw={500}>{o.posting?.title}</Text>
                    <Text size="xs" c="dimmed">{o.posting?.company?.name}</Text>
                  </Stack>
                  <Group gap="sm">
                    <Text size="sm">{o.ctc_lpa ?? "—"} LPA</Text>
                    <StatusBadge status={o.status} />
                  </Group>
                </Group>
              ))}
            </Stack>
          </Card>
        )}
      </Stack>

      <FormModal
        opened={confirm != null} onClose={() => setConfirm(null)}
        title={confirm?.accept ? "Accept this offer?" : "Decline this offer?"}
        subtitle={confirm?.offer.posting?.company?.name}
        onSubmit={act}
        submitLabel={confirm?.accept ? "Accept" : "Decline"}
        danger={!confirm?.accept}
        submitting={respond.isPending}
      >
        <Stack gap="sm">
          {confirm?.accept ? (
            <Alert variant="light" color="orange" icon={<FaExclamationTriangle />}>
              <Text size="sm">
                Accepting records your placement. Depending on institute policy
                this may close your other live applications and prevent you from
                accepting further offers this season.
              </Text>
            </Alert>
          ) : (
            <Text size="sm">
              Declining is final. The offer cannot be reinstated from here.
            </Text>
          )}
        </Stack>
      </FormModal>
    </Container>
  );
}
