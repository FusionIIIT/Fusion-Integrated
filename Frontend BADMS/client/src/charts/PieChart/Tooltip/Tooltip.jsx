/* eslint-disable react/prop-types */
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const SimplePieChart = ( { data }) => {
    return (
        <PieChart width={400} height={400}>
            <Pie
                data={data}
                cx={200}
                cy={200}
                outerRadius={150}
                fill="#8884d8"
                dataKey="value"
                label
            >
                {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
            </Pie>
            <Tooltip />
            <Legend />
        </PieChart>
    );
};

export default SimplePieChart;