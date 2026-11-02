/* eslint-disable react/prop-types */
import { BarChart } from '@mantine/charts';
// import { data } from './data';
import { Title } from '@mantine/core'; // Import for heading

export function Simple({title, data, colors, datakey}) {
    return (
        <div>
            {/* Heading */}
            <Title order={2} align="center" mt="md" mb="lg">
                {title}
            </Title>

            {/* BarChart */}
            <BarChart
                h={250}
                data={data}
                dataKey={datakey}
                series={colors}
                tickLine="y"
                styles={{
                    bar: {
                        transition: '0.3s', // Add smooth transition for hover
                        '&:hover': {
                            fillOpacity: 0.8, // Make it slightly transparent on hover
                        },
                    },
                }}
            />
        </div>
    );
}
