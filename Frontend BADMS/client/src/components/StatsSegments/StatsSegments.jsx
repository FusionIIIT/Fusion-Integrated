import { Progress, Box, Text, Group, Paper, SimpleGrid, rem } from '@mantine/core';
import { FaUsers, FaChartLine } from 'react-icons/fa';
import classes from './StatsSegments.module.css';

const data = [
    { label: 'Students', count: '5,032', part: 88, color: '#47d6ab' },
    { label: 'Professors', count: '64', part: 4, color: '#03141a' },
    { label: 'Others', count: '77', part: 8, color: '#4fcdf7' },
];

export function StatsSegments() {
    const segments = data.map((segment) => (
        <Progress.Section value={segment.part} color={segment.color} key={segment.color}>
            {segment.part > 10 && <Progress.Label>{segment.part}%</Progress.Label>}
        </Progress.Section>
    ));

    const descriptions = data.map((stat) => (
        <Box key={stat.label} style={{ borderBottomColor: stat.color }} className={classes.stat}>
            <Text tt="uppercase" fz="xs" c="dimmed" fw={700}>
                {stat.label}
            </Text>

            <Group justify="space-between" align="flex-end" gap={0}>
                <Text fw={700}>{stat.count}</Text>
                <Text c={stat.color} fw={700} size="sm" className={classes.statCount}>
                    {stat.part}%
                </Text>
            </Group>
        </Box>
    ));

    return (
        <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
                <Group align="flex-end" gap="xs">
                    <Text fz="xl" fw={700}>
                        5,173
                    </Text>
                    <Text c="teal" className={classes.diff} fz="sm" fw={700}>
                        <FaUsers size="1rem" style={{ marginBottom: rem(0) }} />
                        <span>USERS</span>
                    </Text>
                </Group>
                <FaChartLine size="1.4rem" className={classes.icon} />
            </Group>

            <Text c="dimmed" fz="sm">
                Roles Distribution
            </Text>

            <Progress.Root size={34} classNames={{ label: classes.progressLabel }} mt={40}>
                {segments}
            </Progress.Root>
            <SimpleGrid cols={{ base: 1, xs: 3 }} mt="xl">
                {descriptions}
            </SimpleGrid>
        </Paper>
    );
}
