import { useState } from "react";
import { Badge, Container, Tabs } from "@mantine/core";
import { useBatches } from "./hooks/useBatches";
import PageHeader from "../../components/PageHeader/PageHeader";
import UGBatches from "./components/UGBatches";
import PGBatches from "./components/PGBatches";
import PhDBatches from "./components/PhDBatches";

const SECTIONS = {
  ug: UGBatches,
  pg: PGBatches,
  phd: PhDBatches,
};

const TABS = [
  { value: "ug", label: "UG" },
  { value: "pg", label: "PG" },
  { value: "phd", label: "PhD" },
];

const UpcomingBatchesPage = () => {
  const [active, setActive] = useState("ug");
  const { groups, disciplines, curriculums, loading, refresh } = useBatches();

  const ActiveSection = SECTIONS[active];

  return (
    <Container size="xl">
      <PageHeader title="Upcoming Batches" subtitle="Admit and manage UG, PG and PhD batches" />

      <Tabs value={active} onChange={setActive} variant="pills" radius="md" keepMounted={false}>
        <Tabs.List grow mb="lg">
          {TABS.map((tab) => (
            <Tabs.Tab
              key={tab.value}
              value={tab.value}
              rightSection={
                <Badge size="sm" circle variant={active === tab.value ? "white" : "light"} color={active === tab.value ? "blue" : "gray"}>
                  {groups[tab.value]?.length ?? 0}
                </Badge>
              }
            >
              {tab.label}
            </Tabs.Tab>
          ))}
        </Tabs.List>

        <Tabs.Panel value={active}>
          <ActiveSection
            batches={groups[active]}
            disciplines={disciplines}
            curriculums={curriculums}
            loading={loading}
            refresh={refresh}
          />
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
};

export default UpcomingBatchesPage;
