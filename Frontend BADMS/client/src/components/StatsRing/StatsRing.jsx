import { RingProgress, Title, Text, SimpleGrid, Paper, Center, Group, rem, Space } from '@mantine/core';
import {
    FaUserAlt,
    FaArchive,            
    FaUserMinus,
    FaUserCog
} from 'react-icons/fa'; 
import classes from '../FeaturesCards/FeaturesCards.module.css';

const icons = {
    user: FaUserAlt,
    arch: FaArchive,
    del: FaUserMinus,
    role: FaUserCog,
};

const data = [
    { label: 'few minutes ago', stats: 'Notifications Archived', progress: 100, color: 'blue', icon: 'arch' },
    {
        label: 'few minutes ago',
        stats: 'User Deleted',
        progress: 100,
        color: 'red',
        icon: 'del',
    },
    { label: '1 hour ago', stats: 'User Archived', progress: 100, color: 'blue', icon: 'arch' },
    {
        label: '1 hour ago',
        stats: 'User Deleted',
        progress: 100,
        color: 'red',
        icon: 'del',
    },
    { label: '2 hours ago', stats: 'User Created', progress: 100, color: 'teal', icon: 'user' },
    { label: '2 days ago', stats: 'Created Role', progress: 100, color: 'teal', icon: 'role' },
];

export function StatsRing() {
    const stats = data.map((stat) => {
        const Icon = icons[stat.icon];
        return (
            <Paper withBorder radius="md" p="xs" key={stat.label}>
                <Group>
                    <RingProgress
                        size={80}
                        roundCaps
                        thickness={8}
                        sections={[{ value: stat.progress, color: stat.color }]}
                        label={
                            <Center>
                                <Icon style={{ width: rem(20), height: rem(20) }} />
                            </Center>
                        }
                    />

                    <div>
                        <Text c="dimmed" size="xs" tt="uppercase" fw={700}>
                            {stat.label}
                        </Text>
                        <Text fw={700} size="xl">
                            {stat.stats}
                        </Text>
                    </div>
                </Group>
            </Paper>
        );
    });

    return (
        <div>
            <Title order={2} className={classes.title} ta="center" mt="sm">
                Recent Actions
                <Space h="xl" />
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 3 }}>{stats}</SimpleGrid>
        </div>
    );
}
