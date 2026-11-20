import { useState } from "react";
import {
  Alert, Box, Button, Center, Paper, Stack, Text, TextInput,
} from "@mantine/core";
import { FaCheckCircle } from "react-icons/fa";

import { errorMessage } from "../lib/http";
import { BRAND } from "../ui/theme/theme";
import { useRegisterMyCompany } from "./api";

/** PC-UC-014: the request is recorded; the institute decides, and access follows. */
export default function RegisterCompanyPage() {
  const register = useRegisterMyCompany();
  const [form, setForm] = useState({
    name: "", sector: "", website: "", hq_city: "",
    contact_name: "", contact_email: "", contact_phone: "",
  });
  const ready = form.name.trim() && form.contact_name.trim() && form.contact_email.trim();

  function field(key: keyof typeof form) {
    return {
      value: form[key],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
        setForm({ ...form, [key]: e.currentTarget.value }),
    };
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready || register.isPending) return;
    register.mutate(form);
  }

  return (
    <Box mih="100vh" bg="#0c1526">
      <Center mih="100vh" p="md">
        <Paper w={480} p="xl" radius="lg" bg="white">
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
            <Text size="lg" fw={700} mt="sm">Register your company</Text>
            <Text size="sm" c="dimmed">
              The institute reviews each request. You can post roles once it is approved.
            </Text>
          </Stack>

          {register.isSuccess ? (
            <Alert color="green" variant="light" icon={<FaCheckCircle />}
              title="Registration received">
              <Text size="sm">{register.data.detail}</Text>
            </Alert>
          ) : (
            <form onSubmit={submit}>
              <Stack gap="sm">
                <TextInput label="Company name" required maxLength={160} {...field("name")} />
                <TextInput label="Sector" maxLength={60} {...field("sector")} />
                <TextInput label="Website" type="url" placeholder="https://"
                  {...field("website")} />
                <TextInput label="Head office city" maxLength={80} {...field("hq_city")} />
                <TextInput label="Contact person" required maxLength={120}
                  {...field("contact_name")} />
                <TextInput label="Contact email" type="email" required
                  {...field("contact_email")} />
                <TextInput label="Contact phone" maxLength={32} {...field("contact_phone")} />
                {register.isError && (
                  <Alert color="red" variant="light">{errorMessage(register.error)}</Alert>
                )}
                <Button type="submit" disabled={!ready} loading={register.isPending}>
                  Submit registration
                </Button>
                <Text component="a" href="/recruiter/login" size="xs" c={BRAND.primary}>
                  Already approved? Sign in
                </Text>
              </Stack>
            </form>
          )}
        </Paper>
      </Center>
    </Box>
  );
}
