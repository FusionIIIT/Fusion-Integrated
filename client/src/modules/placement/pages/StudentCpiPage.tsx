import { useEffect, useState } from "react";
import {
  Badge, Card, Container, Group, Pagination, Select, Switch, Text, TextInput,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { FaGraduationCap, FaSearch } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCpiDirectory, useCpiFilters, type CpiRow } from "../api/hooks";

const PAGE_SIZE = 50;

/**
 * Every student's latest DECLARED CPI, searchable by discipline and batch.
 *
 * Two care points: an undeclared result reads "not declared", never 0.00, or a
 * missing result becomes a very weak one; and the semester is always on
 * screen, because placement legitimately trails the exam portal.
 */
export default function StudentCpiPage() {
  const [search, setSearch] = useState("");
  const [debounced] = useDebouncedValue(search, 300);
  const [discipline, setDiscipline] = useState<string | null>(null);
  const [batch, setBatch] = useState<string | null>(null);
  const [programme, setProgramme] = useState<string | null>(null);
  const [onlyDeclared, setOnlyDeclared] = useState(false);
  const [page, setPage] = useState(1);

  const filters = useCpiFilters();
  const { data, isPending, error } = useCpiDirectory({
    q: debounced || undefined,
    discipline: discipline || undefined,
    batch_year: batch || undefined,
    programme: programme || undefined,
    only_declared: onlyDeclared || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  // Or page 7 of a narrowed result set reads as "no students in CSE".
  useEffect(() => {
    setPage(1);
  }, [debounced, discipline, batch, programme, onlyDeclared]);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const total = data?.count ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const declared = (data?.results ?? []).filter((r) => r.cpi != null).length;

  return (
    <Container size="xl">
      <PageHeader
        title="Student CPI"
        subtitle="Latest declared result for every student. Read-only — results are owned by the Academic office."
      />

      <Card padding="lg" mb="md">
        <Group gap="sm" wrap="wrap">
          <TextInput
            placeholder="Roll number or name"
            leftSection={<FaSearch size={12} />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            w={260}
          />
          <Select
            placeholder="All disciplines" clearable w={180}
            value={discipline} onChange={setDiscipline}
            data={filters.data?.disciplines ?? []}
            searchable
          />
          <Select
            placeholder="All batches" clearable w={150}
            value={batch} onChange={setBatch}
            data={(filters.data?.batch_years ?? []).map(String)}
          />
          <Select
            placeholder="All programmes" clearable w={170}
            value={programme} onChange={setProgramme}
            data={filters.data?.programmes ?? []}
          />
          <Switch
            label="Declared only" checked={onlyDeclared}
            onChange={(e) => setOnlyDeclared(e.currentTarget.checked)}
          />
          <Text size="sm" c="dimmed" ml="auto">
            {total.toLocaleString()} student{total === 1 ? "" : "s"}
            {data ? ` · ${declared} declared on this page` : ""}
          </Text>
        </Group>
      </Card>

      <Card padding="lg">
        <DataTable<CpiRow>
          rows={data?.results ?? []}
          loading={isPending && !data}
          rowKey={(r) => r.user_id}
          minWidth={980}
          columns={[
            { key: "roll_no", header: "Roll no.",
              render: (r) => <Text fw={600} ff="monospace">{r.roll_no}</Text> },
            { key: "name", header: "Name", render: (r) => r.name || "—" },
            {
              key: "discipline", header: "Discipline",
              render: (r) => r.discipline
                ? <Badge variant="light" size="sm">{r.discipline}</Badge> : "—",
            },
            { key: "programme", header: "Programme",
              render: (r) => r.programme || "—" },
            { key: "batch_year", header: "Batch", align: "right",
              render: (r) => r.batch_year?.toString() ?? "—" },
            {
              key: "cpi", header: "CPI", align: "right",
              render: (r) => r.cpi == null
                // Absent, not zero.
                ? <Text size="sm" c="dimmed">not declared</Text>
                : <Text fw={700}>{r.cpi}</Text>,
            },
            {
              key: "semester", header: "Declared for",
              render: (r) => r.semester == null ? "—" : (
                <Text size="sm">
                  Sem {r.semester}
                  {r.semester_type
                    ? ` (${r.semester_type.replace(" Semester", "")})` : ""}
                </Text>
              ),
            },
            { key: "earned_credits", header: "Credits", align: "right",
              render: (r) => r.earned_credits ?? "—" },
            {
              key: "active_backlogs", header: "Backlogs", align: "right",
              render: (r) => r.active_backlogs == null ? "—" : (
                <Badge
                  color={r.active_backlogs > 0 ? "red" : "gray"}
                  variant="light" size="sm"
                >
                  {r.active_backlogs}
                </Badge>
              ),
            },
          ]}
          empty={{
            icon: FaGraduationCap,
            title: "No students match these filters",
            description: "Try widening the discipline or batch.",
          }}
        />

        {pages > 1 && (
          <Group justify="center" mt="md">
            <Pagination value={page} onChange={setPage} total={pages} size="sm" />
          </Group>
        )}
      </Card>

      <Text size="xs" c="dimmed" mt="sm">
        CPI is the last <b>declared</b> result and can be a semester behind the
        exam portal. Corrections go to the Academic office — the Placement Cell
        does not edit results.
      </Text>
    </Container>
  );
}
