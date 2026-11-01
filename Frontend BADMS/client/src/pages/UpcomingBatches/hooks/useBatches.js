import { useCallback, useEffect, useState } from "react";
import { notifications } from "@mantine/notifications";
import { fetchBatches, fetchCurriculums, fetchDisciplines } from "../../../api/UpcomingBatches";
import { categorizeBatch } from "../config/programmeConfig";

const emptyGroups = { ug: [], pg: [], phd: [] };

export const useBatches = () => {
  const [groups, setGroups] = useState(emptyGroups);
  const [disciplines, setDisciplines] = useState([]);
  const [curriculums, setCurriculums] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [batchData, disciplineData, curriculumData] = await Promise.all([
        fetchBatches(),
        fetchDisciplines(),
        fetchCurriculums(),
      ]);
      const grouped = { ug: [], pg: [], phd: [] };
      (batchData.batches || []).forEach((batch) => {
        const category = categorizeBatch(batch.name);
        if (category) grouped[category].push(batch);
      });
      setGroups(grouped);
      setDisciplines(disciplineData);
      setCurriculums(curriculumData);
    } catch {
      notifications.show({ title: "Error", message: "Failed to load batches.", color: "red" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { groups, disciplines, curriculums, loading, refresh: load };
};
