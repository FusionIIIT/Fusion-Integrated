/* eslint-disable react/prop-types */
import { Group, Paper, SimpleGrid, Text } from '@mantine/core';
import {
    FaUserAlt,
    FaCog,
    FaArchive,
    FaTrash,
    FaVolumeUp,
} from 'react-icons/fa';
import classes from './StatsGrid.module.css';

const icons = {
    user: FaUserAlt,
    settings: FaCog,
    arch: FaArchive,
    del: FaTrash,
    speakerPhone: FaVolumeUp,
};

export function StatsGrid({ data }) {
    const stats = data.map((stat) => {
        const Icon = icons[stat.icon];

        return (
            <Paper withBorder p="md" radius="md" key={stat.title}>
                <Group justify="space-between">
                    <Text size="xs" c="dimmed" className={classes.title}>
                        {stat.title}
                    </Text>
                    <Icon className={classes.icon} size="1.4rem" />
                </Group>

                <Group align="flex-end" gap="xs" mt={25}>
                    <Text className={classes.value}>{stat.value}</Text>
                </Group>

                <Text fz="xs" c="dimmed" mt={7}>
                    <Text className={classes.time}>{stat.time}</Text>
                </Text>
            </Paper>
        );
    });
    return (
        <div className={classes.root}>
            <SimpleGrid cols={{ base: 1, xs: 2, md: data.length }}>{stats}</SimpleGrid>
        </div>
    );
}
