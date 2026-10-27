const express = require('express');
const cors = require('cors');
const { initializeDatabase } = require('./db');
const elmLeaveRoutes = require('./modules/elm/api/routes/elm_leave_routes');

const app = express();

app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'fusion-integrated' });
});

app.use('/api', elmLeaveRoutes);

async function startServer() {
  await initializeDatabase();
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
  });
}

startServer().catch((error) => {
  console.error('Failed to start API server:', error);
  process.exit(1);
});
