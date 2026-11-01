import { useEffect, useState } from 'react';
import { Group, Text, Title, TextInput, Button, Paper, Table, Pagination, Loader } from "@mantine/core";
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { getConfiguration, saveConfiguration, type ConfigurationResponse } from '../api';
import { PageHeader } from '../../../ui/components/PageHeader';
import { errorMessage } from '../../../lib/http';

const ComplaintAdminPage = () => {
  const queryClient = useQueryClient();

  // Fetch configuration data for complaint categories
  const { isLoading: configLoading, error: configError, data: configData } = useQuery<ConfigurationResponse>({
    queryKey: ['config'],
    queryFn: getConfiguration,
  });

  // Form state management
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const form = {
    values: formValues,
    errors: { name: formValues.name ? null : "Category name is required" },
    setValues: (v: any) => setFormValues(v),
    reset: () => setFormValues({}),
    getInputProps: (key: string) => ({
      value: formValues[key] ?? '',
      onChange: (e: any) => setFormValues({ ...formValues, [key]: e.target.value }),
    }),
    submit: () => handleSubmit(formValues),
  };

  // Mutation to add/update a new category
  const { mutateAsync: addOrUpdateCategory } = useMutation({
    mutationFn: (values: Record<string, unknown>) => saveConfiguration(values),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      form.reset();
    },
    onError(error) {
      console.error("Failed to update or create category:", error);
    }
  });

  useEffect(() => {
    if (!configLoading && !configError && configData) {
      form.setValues(configData.categories || []);
    }
  }, [configLoading, configError, configData]);

  // Handle form submission
  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      await addOrUpdateCategory(values);
    } catch (error) {
      console.error("Form submission failed", error);
    }
  };

  // Pagination setup for records
  const [page, setPage] = useState(1);
  const perPage = 20;
  const totalRecords = configData?.recordsCount ?? 0;

  return (
    <Paper shadow="sm" p="md">
      <PageHeader title="Complaint Admin" subtitle="Manage complaint categories and notifications" />
      
      {/* Form to add/update complaint categories */}
      {form.errors.name && <Text c="red">{form.errors.name}</Text>}
      <Group justify="center" mt={30}>
        <TextInput {...form.getInputProps('name')} label="Category Name" required />
        <Button type="submit" onClick={() => form.submit()}>Save Category</Button>
      </Group>

      {/* Display existing categories from configuration data */}
      <Title order={4} mt={50}>Existing Categories</Title>
      <Table striped highlightOnHover>
        <thead>
          <tr>
            <th>Name</th>
          </tr>
        </thead>
        <tbody>
          {configData?.categories.map((category) => (
            <tr key={category.id}>
              <td>{category.name}</td>
            </tr>
          ))}
        </tbody>
      </Table>

      {/* Pagination for records */}
      <Pagination
        value={page}
        onChange={(newPage) => setPage(newPage)}
        total={Math.max(1, Math.ceil(totalRecords / perPage))}
        size="lg"
        mt={20}
      />

      {/* Fetch audit updates/notifications */}
      <Title order={4} mt={50}>Audit Updates and Notifications</Title>
      {configLoading && <Loader />}
      {configError ? <Text c="red">{errorMessage(configError)}</Text> : null}

      {(configData?.records?.length ?? 0) > 0 && (
        <Table striped highlightOnHover>
          <thead>
            <tr>
              <th>ID</th>
              <th>Action</th>
              <th>Description</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {(configData?.records ?? []).slice((page - 1) * perPage, page * perPage).map((record: any) => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>{record.action}</td>
                <td>{record.description}</td>
                <td>{new Date(record.date).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Paper>
  );
};

export default ComplaintAdminPage;
