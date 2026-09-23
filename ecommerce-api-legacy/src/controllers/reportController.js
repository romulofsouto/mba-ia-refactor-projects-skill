const reportService = require('../services/reportService');

async function financialReport(req, res) {
    const report = await reportService.financialReport(req.app.locals.db);
    res.json(report);
}

module.exports = { financialReport };
