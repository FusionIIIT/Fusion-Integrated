// path/to/app.js
import express from 'express';
import bodyParser from 'body-parser';
import cors from 'cors';
import { sequelize } from './db';
import elmLeaveRoutes from './modules/elm/routes/elm_leave_routes';

const app = express();
app.use(bodyParser.json());
app.use(cors());

sequelize.sync({ force: false }).then(() => {
  console.log('Database synced');
});

app.use('/api', elmLeaveRoutes);

app.listen(3000, () => {
  console.log('Server is running on port 3000');
});
