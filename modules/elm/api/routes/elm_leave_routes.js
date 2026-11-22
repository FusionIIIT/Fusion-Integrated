const express = require('express');
const controller = require('../../controllers/elm_leave_controller');

const router = express.Router();

router.use('/', controller);

module.exports = router;
