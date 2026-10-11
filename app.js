const express = require('express');
const bodyParser = require('body-parser');
const leaveRoutes = require('./routes/leave');

const app = express();
const port = 3000;

app.use(bodyParser.json());
app.use('/api/leave', leaveRoutes);

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
