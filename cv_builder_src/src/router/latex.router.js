const express = require('express');
const latexController = require('../controller/latex.controller');

const router = express.Router();

router.post('/compile', latexController.compile);

module.exports = router;
