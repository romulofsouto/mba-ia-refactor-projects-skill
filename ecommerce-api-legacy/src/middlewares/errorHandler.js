const logger = require('../config/logger');

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
    if (err.type === 'entity.parse.failed') return res.status(400).send('Bad Request');

    logger.error('unhandled error', { method: req.method, path: req.path, error: err.message, stack: err.stack });
    res.status(500).send('Erro interno');
}

module.exports = errorHandler;
