import { Alert, List, Loader, Stack, Text, ThemeIcon } from "@mantine/core";
import { FaCheckCircle, FaExclamationTriangle, FaTimesCircle } from "react-icons/fa";
import type { AxiosError } from "axios";

import { CpiBadge } from "./CpiBadge";
import type { EligibilityVerdict } from "../api/types";

/** Why a student can or cannot apply.
 *
 *  The whole point is the per-rule reason list. "Not eligible" produces a
 *  support ticket; "CPI 6.80 — this posting needs at least 7.00" does not. The
 *  server composes each message, so nothing here has to interpret a rule code.
 */
export function EligibilityPanel({ verdict, isPending, error }: {
  verdict?: EligibilityVerdict;
  isPending: boolean;
  error: unknown;
}) {
  if (isPending) {
    return (
      <Alert variant="light" color="gray">
        <Loader size="xs" mr={8} /> Checking your eligibility…
      </Alert>
    );
  }

  // On a 503 the standing is unknown; "not eligible" would be a lie acted on.
  if ((error as AxiosError)?.response?.status === 503) {
    return (
      <Alert
        variant="light" color="yellow" icon={<FaExclamationTriangle />}
        title="Eligibility cannot be checked right now"
      >
        <Text size="sm">
          Academic records are temporarily unavailable, so we cannot confirm
          whether you meet this posting&apos;s criteria. Please try again
          shortly — this is not a decision about your application.
        </Text>
      </Alert>
    );
  }

  if (error || !verdict) {
    return (
      <Alert variant="light" color="red" icon={<FaExclamationTriangle />}>
        <Text size="sm">Could not check eligibility for this posting.</Text>
      </Alert>
    );
  }

  if (verdict.is_eligible) {
    return (
      <Alert
        variant="light" color="green" icon={<FaCheckCircle />}
        title="You are eligible for this posting"
      >
        <Stack gap={6}>
          <Text size="sm">Your application will be recorded against:</Text>
          <CpiBadge cpi={verdict.cpi} standing={verdict.standing} />
        </Stack>
      </Alert>
    );
  }

  const reasons = verdict.failed ?? [];
  const seasonBlocked = verdict.season_decision
    && !verdict.season_decision.allowed;

  return (
    <Alert
      variant="light" color="orange" icon={<FaTimesCircle />}
      title="You cannot apply to this posting yet"
    >
      <Stack gap={8}>
        {seasonBlocked && (
          <Text size="sm" fw={500}>{verdict.season_decision.message}</Text>
        )}
        {reasons.length > 0 && (
          <List
            spacing={4} size="sm"
            icon={
              <ThemeIcon color="orange" size={16} radius="xl" variant="light">
                <FaTimesCircle size={9} />
              </ThemeIcon>
            }
          >
            {reasons.map((r, i) => (
              <List.Item key={`${r.field}-${i}`}>{r.message}</List.Item>
            ))}
          </List>
        )}
        {!seasonBlocked && reasons.length === 0 && (
          <Text size="sm">This posting is not open to you.</Text>
        )}
      </Stack>
    </Alert>
  );
}
