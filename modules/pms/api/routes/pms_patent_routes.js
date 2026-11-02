const express = require('express');
const controller = require('../../controllers/pms_patent_controller');

const router = express.Router();

router.use('/', controller);

module.exports = router;
