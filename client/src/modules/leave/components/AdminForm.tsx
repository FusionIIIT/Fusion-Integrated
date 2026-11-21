import { useState } from "react";
import { Button, Card, Group, Select, SimpleGrid, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useAdminWrite } from "../api/hooks";

export interface Field {
  name: string;
  label: string;
  type?: "text" | "date" | "number" | "select";
  options?: string[];
  optional?: boolean;
}

/** A small card form for one admin endpoint; empty optional fields go as null. */
export function AdminForm({ title, method = "post", path, fields, transform }: {
  title: string;
  method?: "post" | "put";
  path: string;
  fields: Field[];
  transform?: (v: Record<string, unknown>) => unknown;
}) {
  const write = useAdminWrite();
  const [values, setValues] = useState<Record<string, string>>({});
  const missing = fields.some((f) => !f.optional && !values[f.name]);

  function submit() {
    const body: Record<string, unknown> = {};
    for (const f of fields) {
      const v = values[f.name] ?? "";
      body[f.name] = f.type === "number" ? (v === "" ? null : Number(v)) : v;
    }
    write.mutate({ method, path, body: transform ? transform(body) : body }, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Saved", message: title });
        setValues({});
      },
      onError: (e) => notifications.show({ color: "red", title: "Not saved",
        message: errorMessage(e) }),
    });
  }

  return (
    <Card withBorder padding="md" mb="md">
      <Text fw={600} mb="xs">{title}</Text>
      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
        {fields.map((f) => f.type === "select" ? (
          <Select key={f.name} label={f.label} data={f.options ?? []}
            value={values[f.name] ?? null} clearable={f.optional}
            onChange={(v) => setValues((s) => ({ ...s, [f.name]: v ?? "" }))} />
        ) : (
          <TextInput key={f.name} label={f.label} required={!f.optional}
            type={f.type === "date" ? "date" : "text"} value={values[f.name] ?? ""}
            inputMode={f.type === "number" ? "decimal" : undefined}
            onChange={(e) => {
              const v = e.currentTarget.value;
              setValues((s) => ({ ...s, [f.name]: v }));
            }} />
        ))}
      </SimpleGrid>
      <Group justify="flex-end" mt="sm">
        <Button size="sm" onClick={submit} disabled={missing} loading={write.isPending}>
          Save
        </Button>
      </Group>
    </Card>
  );
}
