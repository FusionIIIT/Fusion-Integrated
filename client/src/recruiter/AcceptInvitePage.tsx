import { useState } from "react";
import {
  Alert, Box, Button, Center, List, Paper, PasswordInput, Progress, Stack, Text,
  Title,
} from "@mantine/core";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FaCheckCircle, FaExclamationTriangle } from "react-icons/fa";

import { errorMessage } from "../lib/http";
import { BRAND } from "../ui/theme/theme";
import { useAcceptInvite } from "./api";

const MIN_LENGTH = 12;

/** Client-side guidance only. The server enforces the minimum length, and this
 *  meter exists so a recruiter is not told "too short" after submitting. */
function strength(pw: string): { score: number; hints: string[] } {
  const hints: string[] = [];
  if (pw.length < MIN_LENGTH) hints.push(`At least ${MIN_LENGTH} characters`);
  if (!/[a-z]/.test(pw) || !/[A-Z]/.test(pw)) hints.push("Mix upper and lower case");
  if (!/[0-9]/.test(pw)) hints.push("Include a number");
  if (!/[^A-Za-z0-9]/.test(pw)) hints.push("Include a symbol");
  const met = 4 - hints.length;
  return { score: Math.max(0, (met / 4) * 100), hints };
}

export default function AcceptInvitePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const accept = useAcceptInvite();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);

  const { score, hints } = strength(password);
  const mismatch = confirm.length > 0 && confirm !== password;
  const ready = password.length >= MIN_LENGTH && !mismatch && confirm.length > 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (accept.isPending || !ready) return;
    accept.mutate({ token, password }, { onSuccess: () => setDone(true) });
  }

  return (
    <Box mih="100vh" bg="#0c1526">
      <Center mih="100vh" p="md">
        <Paper w={440} p="xl" radius="lg" bg="white">
          <Stack gap={4} mb="lg">
            <Text fw={900} size="sm" lts={1} c="#0b1220">
              PDPM IIITDM <span style={{ color: BRAND.primary }}>JABALPUR</span>
            </Text>
            <Text
              size="xs" c="dimmed" fw={800}
              style={{ fontFamily: "monospace", letterSpacing: 2 }}
            >
              FUSION · PLACEMENT
            </Text>
          </Stack>

          {!token ? (
            <Alert color="red" variant="light" icon={<FaExclamationTriangle />}
              title="This link is incomplete">
              <Text size="sm">
                The invitation link is missing its token. Ask the placement
                office to send a new invitation.
              </Text>
            </Alert>
          ) : done ? (
            <Stack gap="md">
              <Alert color="green" variant="light" icon={<FaCheckCircle />}
                title="Your password is set">
                <Text size="sm">You can now sign in to the recruiter portal.</Text>
              </Alert>
              <Button onClick={() => navigate("/recruiter/login")} fullWidth>
                Go to sign in
              </Button>
            </Stack>
          ) : (
            <>
              <Title order={3} mb={4}>Set your password</Title>
              <Text c="dimmed" size="sm" mb="lg">
                Choose a password for your recruiter account. This invitation
                can only be used once.
              </Text>

              <form onSubmit={submit}>
                <Stack gap="md">
                  {accept.error != null && (
                    <Alert color="red" variant="light"
                      icon={<FaExclamationTriangle />}>
                      <Text size="sm">{errorMessage(accept.error)}</Text>
                      <Text size="xs" c="dimmed" mt={4}>
                        Invitations expire after 72 hours. If yours has lapsed,
                        ask the placement office for a new one.
                      </Text>
                    </Alert>
                  )}

                  <PasswordInput
                    label="New password" required value={password}
                    onChange={(e) => setPassword(e.currentTarget.value)}
                    autoComplete="new-password"
                  />
                  {password.length > 0 && (
                    <div>
                      <Progress
                        value={score} size="sm"
                        color={score === 100 ? "teal" : score >= 50 ? "yellow"
                          : "red"}
                      />
                      {hints.length > 0 && (
                        <List size="xs" c="dimmed" mt={6} spacing={2}>
                          {hints.map((h) => <List.Item key={h}>{h}</List.Item>)}
                        </List>
                      )}
                    </div>
                  )}

                  <PasswordInput
                    label="Confirm password" required value={confirm}
                    onChange={(e) => setConfirm(e.currentTarget.value)}
                    error={mismatch ? "Passwords do not match" : undefined}
                    autoComplete="new-password"
                  />

                  <Button
                    type="submit" fullWidth loading={accept.isPending}
                    disabled={!ready}
                  >
                    Set password
                  </Button>
                </Stack>
              </form>
            </>
          )}
        </Paper>
      </Center>
    </Box>
  );
}
