import { TextInput, Select, Textarea, Button, Card, Title, Stack, Group, Alert } from '@mantine/core';
import { useForm } from '@mantine/form';

const BookingRequestPage = () => {
  const form = useForm({
    initialValues: {
      visitorName: '',
      email: '',
      phone: '',
      visitorCategory: 'A',
      arrivalDate: '',
      departureDate: '',
      billingResponsibility: 'Visitor',
      purposeOfStay: ''
    },
  });

  const submitBooking = (values) => {
    console.log(values); // Replace this with your actual booking submission logic
    form.reset();
  };

  return (
    <Card shadow="sm" p="lg" radius="md" withBorder>
      <Title order={2}>Booking Request</Title>
      <form onSubmit={form.onSubmit(submitBooking)}>
        <Stack>
          <TextInput label="Visitor Name" {...form.getInputProps('visitorName')} />
          <TextInput label="Email" {...form.getInputProps('email')} />
          <TextInput label="Phone" {...form.getInputProps('phone')} />
          <Select 
            label="Visitor Category" 
            data={['A', 'B', 'C', 'D']} 
            {...form.getInputProps('visitorCategory')} 
          />
          <TextInput label="Arrival Date" type="date" {...form.getInputProps('arrivalDate')} />
          <TextInput label="Departure Date" type="date" {...form.getInputProps('departureDate')} />
          <Select 
            label="Billing Responsibility" 
            data={['Visitor', 'Indenter', 'Institute', 'Project']} 
            {...form.getInputProps('billingResponsibility')} 
          />
          <Textarea label="Purpose of Stay" {...form.getInputProps('purposeOfStay')} />
        </Stack>
        <Group mt="md" position="right">
          <Button type="submit">Submit</Button>
        </Group>
      </form>
      {/* Confirmation Alert */}
      <Alert mt="lg" title="Booking Submitted!" color="green">Your booking request has been submitted successfully.</Alert>
    </Card>
  );
};

export default BookingRequestPage;
