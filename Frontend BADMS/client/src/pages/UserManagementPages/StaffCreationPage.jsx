import { useState, useEffect } from 'react';
import {
    TextInput,
    Select,
    Button,
    Grid,
    Group,
    Container,
    NumberInput,
    Radio,
    rem,
    Progress,
    Card,
    Text,
    Divider,
} from '@mantine/core';
import { FaCheck, FaTimes } from 'react-icons/fa';
import { showNotification } from '@mantine/notifications';
import { DateInput } from '@mantine/dates';
import { getAllDesignations, getAllDepartments } from '../../api/Roles';
import { createStaff } from '../../api/Users';
import PageHeader from '../../components/PageHeader/PageHeader';

const StaffCreationPage = () => {
    const xIcon = <FaTimes style={{ width: rem(20), height: rem(20) }} />;
    const checkIcon = <FaCheck style={{ width: rem(20), height: rem(20) }} />;

    const [formValues, setFormValues] = useState({
        username: '',
        first_name: '',
        last_name: '',
        department: '',
        title: '',
        designation: '',
        sex: '',
        dob: null,
        phone: '',
        address: '',
    });

    const [progress, setProgress] = useState(0);
    const [roles, setRoles] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [, setLoading] = useState(false);
    const [, setErrorMessage] = useState('');

    useEffect(() => {
        const totalFields = Object.keys(formValues).length;
        const filledFields = Object.values(formValues).filter((value) => value).length;
        setProgress((filledFields / totalFields) * 100);
    }, [formValues]);

    const handleChange = (field, value) => {
        setFormValues((prev) => ({ ...prev, [field]: value }));
        setErrorMessage('');
    };

    const fetchStaffDesignations = async () => {
        try {
            let all_designations = [];
            const designationData = {
                category: 'staff',
                basic: true,
            }
            const response = await getAllDesignations(designationData);
            console.log(response)
            for(let i=0; i<response.length; i++){
                all_designations[i] = {value: `${response[i].id}`, label: response[i].name}
            }
            setRoles(all_designations);
        } catch {
            showNotification({
                title: 'Error',
                icon: xIcon,
                position: "top-center",
                withCloseButton: true,
                message: 'An error occurred while fetching designations.',
                color: 'red',
            });
        }
    }

    const fetchDepartments = async () => {
        try {
            let all_departments = [];
            const response = await getAllDepartments();
            console.log(response)
            for(let i=0; i<response.length; i++){
                all_departments[i] = {value: `${response[i].id}`, label: response[i].name}
            }
            setDepartments(all_departments);
        } catch {
            showNotification({
                title: 'Error',
                icon: xIcon,
                position: "top-center",
                withCloseButton: true,
                message: 'An error occurred while fetching departments.',
                color: 'red',
            });
        }
    }

    const handleSubmit = async () => {
        console.log(formValues)
        try{
            setLoading(true)
            await createStaff(formValues);
            showNotification({
                icon: checkIcon,
                title: "Success",
                position: "top-center",
                withCloseButton: true,
                autoClose: 5000,
                message: "Staff Created Successfully.",
                color: "green",
            });
            console.log('Form Submitted', formValues);
            setFormValues({
                username: '',
                first_name: '',
                last_name: '',
                department: '',
                title: '',
                designation: '',
                sex: '',
                dob: null,
                phone: '',
                address: '',
            });
        } catch {
            showNotification({
                title: 'Error',
                icon: xIcon,
                position: "top-center",
                withCloseButton: true,
                message: 'An error occurred while creating staff.',
                color: 'red',
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(()=>{
        fetchStaffDesignations();
        fetchDepartments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    },[])

    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                handleSubmit();
            }
        };

        window.addEventListener('keydown', handleKeyDown);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [formValues]);

    return (
        <Container size="lg">
            <PageHeader
                title="Add Staff"
                subtitle="Create a new staff account with department, designation and personal details."
            />
            <Card padding="lg" withBorder radius="lg">
                <Progress value={progress} size="sm" radius="xl" mb="lg" />

                <Text fw={700} size="xs" tt="uppercase" c="dimmed" mt="md" mb={4}>
                    Identity
                </Text>
                <Divider mb="md" />
                <Grid gutter="md">
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput
                            label="Username"
                            placeholder="Enter username(20 letters)"
                            value={formValues.username}
                            onChange={(e) => handleChange('username', e.target.value)}
                            required
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput
                            label="First Name"
                            placeholder="Enter first name"
                            value={formValues.first_name}
                            onChange={(e) => handleChange('first_name', e.target.value)}
                            required
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput
                            label="Last Name"
                            placeholder="Enter last name"
                            value={formValues.last_name}
                            onChange={(e) => handleChange('last_name', e.target.value)}
                            required
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <Select
                            label="Department"
                            placeholder="Enter department"
                            data={departments}
                            value={`${formValues.department}`}
                            onChange={(value) => handleChange('department', Number(value))}
                            size="md"
                        />
                    </Grid.Col>
                </Grid>

                <Text fw={700} size="xs" tt="uppercase" c="dimmed" mt="md" mb={4}>
                    Details
                </Text>
                <Divider mb="md" />
                <Grid gutter="md">
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <Select
                            label="Title"
                            placeholder="Select title"
                            data={['Dr.', 'Mr.', 'Mrs.', 'Ms.']}
                            value={formValues.title}
                            onChange={(value) => handleChange('title', value)}
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <Select
                            label="Designation"
                            placeholder="Select designation"
                            data={roles}
                            value={`${formValues.designation}`}
                            onChange={(value) => handleChange('designation', Number(value))}
                            required
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={12}>
                        <Radio.Group
                            label="Gender"
                            value={formValues.sex}
                            onChange={(value) => handleChange('sex', value)}
                            required
                            styles={{
                                label: { marginRight: '1rem' },
                            }}
                        >
                            <Group spacing="sm" position="apart" mt="xs">
                                <Radio value="male" label="Male" />
                                <Radio value="female" label="Female" />
                                {/* <Radio value="other" label="Other" /> */}
                            </Group>
                        </Radio.Group>
                    </Grid.Col>
                </Grid>

                <Text fw={700} size="xs" tt="uppercase" c="dimmed" mt="md" mb={4}>
                    Contact
                </Text>
                <Divider mb="md" />
                <Grid gutter="md">
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <DateInput
                            value={formValues.dob}
                            onChange={(value) => handleChange('dob', value)}
                            label="Date of Birth"
                            placeholder="Pick a date"
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                        <NumberInput
                            label="Phone Number"
                            placeholder="Enter phone number"
                            value={formValues.phone}
                            onChange={(value) => handleChange('phone', value)}
                            hideControls
                            size="md"
                        />
                    </Grid.Col>
                    <Grid.Col span={12}>
                        <TextInput
                            label="Address"
                            placeholder="Enter address"
                            value={formValues.address}
                            onChange={(e) => handleChange('address', e.target.value)}
                            size="md"
                        />
                    </Grid.Col>
                </Grid>

                <Group justify="flex-end" mt="lg">
                    <Button onClick={handleSubmit} size="md">
                        Add Staff
                    </Button>
                </Group>
            </Card>
        </Container>
    );
};

export default StaffCreationPage;
