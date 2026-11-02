/* eslint-disable react/prop-types */
import React, { useState, useEffect, useMemo } from "react";
import {
  Tabs,
  Card,
  Text,
  Badge,
  ScrollArea,
  Container,
  TextInput,
  MultiSelect,
  Grid,
  Group,
  Loader,
  Paper,
  Center,
  Divider,
} from "@mantine/core";
import { debounce } from "lodash";
import { VariableSizeList as List } from "react-window";
import { fetchUsersByType } from "../../api/Users.jsx";
import PageHeader from "../../components/PageHeader/PageHeader";

const InfoCard = React.memo(function InfoCard({ person }) {
  return (
  <Card shadow="xs" radius="md" withBorder p="lg">
    <Group justify="space-between" align="flex-start" wrap="nowrap" mb="xs">
      <Text fw={600} size="lg">
        {person.full_name}
      </Text>
      <Badge variant="light" radius="sm">
        {person.user_type}
      </Badge>
    </Group>
    <Text size="sm" c="dimmed">
      <strong>Username:</strong> {person.username}
    </Text>

    {person.user_type === "student" && (
      <>
        <Divider my="sm" />
        <Text size="sm">
          <strong>Programme:</strong> {person.programme}
        </Text>
        <Text size="sm">
          <strong>Discipline:</strong> {person.discipline}
        </Text>
        <Text size="sm">
          <strong>Batch:</strong> {person.batch}
        </Text>
        <Text size="sm">
          <strong>Semester:</strong> {person.curr_semester_no}
        </Text>
        <Group gap="xs" mt={4} mb={4}>
          <Text size="sm">
            <strong>Category:</strong>
          </Text>
          <Badge variant="light" color="grape" radius="sm">
            {person.category}
          </Badge>
        </Group>
        <Text size="sm">
          <strong>Gender:</strong> {person.gender}
        </Text>
      </>
    )}

    {person.user_type === "staff" && (
      <>
        <Divider my="sm" />
        <Text size="sm">
          <strong>Gender:</strong> {person.gender}
        </Text>
      </>
    )}

    {person.user_type === "faculty" && (
      <>
        <Divider my="sm" />
        <Text size="sm">
          <strong>Department:</strong> {person.department}
        </Text>
        <Text size="sm">
          <strong>Gender:</strong> {person.gender}
        </Text>
        <Text size="sm" mb="xs">
          <strong>Designations:</strong>
        </Text>
        <Group gap="xs">
          {person.designations.map((role, idx) => (
            <Badge key={idx} color="indigo" variant="light" radius="sm">
              {role}
            </Badge>
          ))}
        </Group>
      </>
    )}
  </Card>
  );
});

const extractUnique = (arr, key) => [
  ...new Set(
    arr
      .flatMap((item) => {
        if (key === "semester") return String(item.curr_semester_no);
        if (key === "designations") return item.designations || [];
        return item[key] ? String(item[key]) : [];
      })
      .filter(Boolean),
  ),
];

const filterAndSearch = (data, filters, searchQuery) =>
  (Array.isArray(data) ? data : []).filter((person) => {
    const matchSearch =
      person.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      person.username.toLowerCase().includes(searchQuery.toLowerCase());

    const matchFilters = Object.entries(filters).every(([key, values]) => {
      if (values.length === 0) return true;
      if (key === "semester")
        return values.includes(String(person.curr_semester_no));
      if (key === "designations")
        return person.designations?.some((d) => values.includes(d));
      return values.includes(String(person[key]));
    });

    return matchSearch && matchFilters;
  });

const UserDirectory = () => {
  const [activeTab, setActiveTab] = useState("student");
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    programme: [],
    discipline: [],
    batch: [],
    category: [],
    department: [],
    semester: [],
    designations: [],
    gender: [],
  });
  const [data, setData] = useState({ student: [], faculty: [], staff: [] });
  const [loading, setLoading] = useState(false);
  const [filtering, setFiltering] = useState(false);

  const resetFilters = () =>
    setFilters({
      programme: [],
      discipline: [],
      batch: [],
      category: [],
      department: [],
      semester: [],
      designations: [],
      gender: [],
    });

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetchUsersByType(activeTab);
        setData((prev) => ({ ...prev, [activeTab]: res || [] }));
      } catch (err) {
        console.error("Failed to load data:", err);
      } finally {
        setLoading(false);
        resetFilters();
        setSearchQuery("");
      }
    };

    fetchData();
  }, [activeTab]);

  const currentData = useMemo(() => data[activeTab] || [], [data, activeTab]);

  const applicableFilters =
    activeTab === "student"
      ? ["programme", "discipline", "batch", "semester", "category", "gender"]
      : activeTab === "faculty"
        ? ["department", "designations", "gender"]
        : ["gender"];

  const handleSearchChange = useMemo(
    () =>
      debounce((value) => {
        setFiltering(true);
        setSearchQuery(value);
        setTimeout(() => setFiltering(false), 200);
      }, 200),
    [],
  );

  const filteredData = useMemo(
    () => filterAndSearch(currentData, filters, searchQuery),
    [currentData, filters, searchQuery],
  );

  const hasActiveQuery =
    searchQuery.trim() !== "" ||
    Object.values(filters).some((values) => values.length > 0);

  const semesterOptions = extractUnique(data.student, "semester");
  const facultyDesignations = extractUnique(data.faculty, "designations");

  const getItemSize = (index) => {
    const user = filteredData[index];
    if (user.user_type === "student") return 270;
    if (user.user_type === "faculty") return 250;
    return 150;
  };

  const VirtualList = () => (
    <List
      height={500}
      itemCount={filteredData.length}
      itemSize={getItemSize}
      width="100%"
      overscanCount={5}
    >
      {({ index, style }) => (
        <div style={{ ...style, padding: "0 8px", boxSizing: "border-box" }}>
          <div style={{ marginBottom: 12 }}>
            <InfoCard person={filteredData[index]} />
          </div>
        </div>
      )}
    </List>
  );

  return (
    <Container size="xl">
      <PageHeader
        title="User Directory"
        subtitle="Search and filter students, faculty and staff across the institute"
      />

      <Paper p="lg" radius="lg" withBorder>
        <Tabs
          value={activeTab}
          onChange={setActiveTab}
          variant="pills"
          radius="md"
          keepMounted={false}
        >
          <Tabs.List grow mb="lg">
            <Tabs.Tab value="student">STUDENTS</Tabs.Tab>
            <Tabs.Tab value="faculty">FACULTY</Tabs.Tab>
            <Tabs.Tab value="staff">STAFF</Tabs.Tab>
          </Tabs.List>

          {["student", "faculty", "staff"].map((tabKey) => (
            <Tabs.Panel value={tabKey} key={tabKey}>
              <Grid mb="lg">
                <Grid.Col span={12}>
                  <TextInput
                    size="md"
                    radius="md"
                    placeholder="Search by name or username"
                    onChange={(e) => handleSearchChange(e.currentTarget.value)}
                  />
                </Grid.Col>

                {applicableFilters.map((filterKey, idx) => (
                  <Grid.Col span={6} key={idx}>
                    <MultiSelect
                      label={filterKey[0].toUpperCase() + filterKey.slice(1)}
                      size="md"
                      placeholder={`Filter by ${filterKey}`}
                      radius="md"
                      value={filters[filterKey]}
                      onChange={(value) =>
                        setFilters((prev) => ({ ...prev, [filterKey]: value }))
                      }
                      data={
                        filterKey === "semester"
                          ? semesterOptions
                          : filterKey === "designations"
                            ? facultyDesignations
                            : extractUnique(currentData, filterKey)
                      }
                      clearable
                      searchable
                    />
                  </Grid.Col>
                ))}
              </Grid>

              {loading || filtering ? (
                <Center h={200}>
                  <Loader size="md" />
                </Center>
              ) : !hasActiveQuery ? (
                <Center h={200}>
                  <Text ta="center" c="dimmed" size="sm">
                    Search by name or username, or apply a filter, to view users.
                  </Text>
                </Center>
              ) : filteredData.length > 0 ? (
                <ScrollArea h={500} offsetScrollbars>
                  <VirtualList />
                </ScrollArea>
              ) : (
                <Center h={200}>
                  <Text ta="center" c="dimmed" size="sm">
                    No users found.
                  </Text>
                </Center>
              )}
            </Tabs.Panel>
          ))}
        </Tabs>
      </Paper>
    </Container>
  );
};

export default UserDirectory;
