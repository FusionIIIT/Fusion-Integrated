import {
  Button, Card, Checkbox, Group, Select, Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { FormSection } from "../../../ui/components/FormSection";
import { errorMessage } from "../../../lib/http";
import { usePmsAction, type PmsMethod } from "../api/hooks";

export interface PmsField {
  name: string;
  label: string;
  type?: "text" | "email" | "number" | "date" | "textarea" | "select" | "checkbox";
  required?: boolean;
  description?: string;
  options?: Array<{ value: string; label: string }>;
  initialValue?: string | boolean;
}

export function PmsActionForm({
  title, fields, method = "post", path, submitLabel = "Submit",
  successTitle = "Request completed", successMessage = "The server accepted the request.",
  transform, afterSuccess, compact = false,
}: {
  title: string;
  fields: PmsField[];
  method?: PmsMethod;
  path: (body: Record<string, unknown>) => string;
  submitLabel?: string;
  successTitle?: string;
  successMessage?: string;
  transform?: (values: Record<string, string | boolean>) => Record<string, unknown>;
  afterSuccess?: (response: unknown) => void;
  compact?: boolean;
}) {
  const initial = Object.fromEntries(fields.map((f) => [f.name, f.initialValue ?? ""]));
  const [values, setValues] = useState<Record<string, string | boolean>>(initial);
  const [validationError, setValidationError] = useState("");
  const action = usePmsAction(method, path);

  function update(name: string, value: string | boolean) {
    setValues((previous) => ({ ...previous, [name]: value }));
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const missing = fields.find((field) => {
      const value = values[field.name];
      return field.required && (typeof value === "boolean" ? !value : !String(value ?? "").trim());
    });
    if (missing) {
      setValidationError(`${missing.label} is required.`);
      return;
    }
    setValidationError("");
    const body = transform ? transform(values) : values;
    action.mutate(body, {
      onSuccess: (response) => {
        notifications.show({ color: "green", title: successTitle, message: successMessage });
        setValues(initial);
        afterSuccess?.(response);
      },
    });
  }

  return (
    <Card padding={compact ? "md" : "lg"}>
      <form onSubmit={submit}>
        <Stack gap="md">
          <FormSection title={title} first>
            <Stack gap="sm">
              {fields.map((field) => {
                const value = values[field.name];
                if (field.type === "checkbox") {
                  return (
                    <Checkbox
                      key={field.name}
                      label={field.label}
                      description={field.description}
                      required={field.required}
                      checked={Boolean(value)}
                      onChange={(event) => update(field.name, event.currentTarget.checked)}
                    />
                  );
                }
                if (field.type === "textarea") {
                  return (
                    <Textarea
                      key={field.name} label={field.label} required={field.required}
                      description={field.description} minRows={3} autosize
                      value={String(value ?? "")}
                      onChange={(event) => update(field.name, event.currentTarget.value)}
                    />
                  );
                }
                if (field.type === "select") {
                  return (
                    <Select
                      key={field.name} label={field.label} required={field.required}
                      description={field.description}
                      data={field.options ?? []} value={String(value || "") || null}
                      onChange={(next) => update(field.name, next ?? "")}
                      searchable
                    />
                  );
                }
                return (
                  <TextInput
                    key={field.name} type={field.type ?? "text"}
                    label={field.label} required={field.required}
                    description={field.description}
                    value={String(value ?? "")}
                    onChange={(event) => update(field.name, event.currentTarget.value)}
                  />
                );
              })}
            </Stack>
          </FormSection>
          {action.error && <ErrorState error={action.error} />}
          {validationError && <Text size="sm" c="red" role="alert">{validationError}</Text>}
          <Group justify="space-between" align="center">
            <Text size="xs" c="dimmed">
              {action.error ? errorMessage(action.error) : "Changes are validated by PMS before they are saved."}
            </Text>
            <Button type="submit" loading={action.isPending}>
              {submitLabel}
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );
}
