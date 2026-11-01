import { useState } from 'react';
import {
    Container,
    Card,
    Button,
    Group,
    Text,
    Stack,
    rem,
    Modal,
    TextInput,
} from '@mantine/core';

import { showNotification } from '@mantine/notifications';
import '@mantine/notifications/styles.css';
import { FaCheck, FaTimes } from 'react-icons/fa';
import { resetPassword } from '../../api/Users';
import PageHeader from '../../components/PageHeader/PageHeader';

const ResetUserPasswordPage = () => {
    const [formData, setFormData] = useState({
        username: '',
    });

    const [errorMessage, setErrorMessage] = useState('');
    const [opened, setOpened] = useState(false);


    const xIcon = <FaTimes style={{ width: rem(20), height: rem(20) }} />;
    const checkIcon = <FaCheck style={{ width: rem(20), height: rem(20) }} />;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prevData) => ({
            ...prevData,
            [name]: value,
        }));
        setErrorMessage(''); // Clear error when user starts typing
    };

    const openConfirmationDialog = () => {
        if (formData.username.trim() === '') {
            setErrorMessage('Please enter username.');
        } else {
            setOpened(true);
        }
    };

    const handleSubmit = async () => {
        try {
            setOpened(false);
            await resetPassword(formData);
            close();
            showNotification({
                title: 'Password Reset',
                icon: checkIcon,
                position: "top-center",
                withCloseButton: true,
                message: `Password for ${formData.name} has been reset. The new password has been emailed to the user.`,
                color: 'green',
            });
            setFormData({
                name: '',
                rollNo: '',
            });
        }
        catch {
            showNotification({
                title: 'Error',
                icon: xIcon,
                position: "top-center",
                withCloseButton: true,
                message: 'An error occurred while resetting password.   ',
                color: 'red',
            });
        }
    };

    return (
        <Container size="lg">
            <PageHeader
                title="Reset Password"
                subtitle="Generate a new password for a user; it is emailed directly to them."
            />

            <Card
                padding="lg"
                withBorder
                radius="lg"
                style={{
                    width: '100%',
                    maxWidth: '480px',
                    margin: '0 auto',
                }}
            >
                <form>
                    <Stack spacing="md">
                        <TextInput
                            label="UserName"
                            name="username"
                            placeholder="Enter user name"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            size="md"
                        />

                        {errorMessage && (
                            <Text c="red" style={{ fontSize: '14px' }}>
                                {errorMessage}
                            </Text>
                        )}
                    </Stack>

                    <Group justify="flex-end" mt="lg">
                        <Button onClick={openConfirmationDialog} size="md">
                            Reset Password
                        </Button>
                    </Group>
                </form>
            </Card>

            {/* Confirmation Modal */}
            <Modal
                opened={opened}
                onClose={() => setOpened(false)}
                title="Reset Password"
            >
                <Text>
                    Are you sure you want to reset the password for {formData.username}?
                </Text>
                <Group justify="flex-end" mt="md">
                    <Button variant="default" onClick={() => setOpened(false)}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit}>
                        Confirm
                    </Button>
                </Group>
            </Modal>
        </Container>
    );
};

export default ResetUserPasswordPage;
