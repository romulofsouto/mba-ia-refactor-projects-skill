const express = require('express');
const config = require('./config');
const logger = require('./config/logger');
const database = require('./config/database');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');

async function start() {
    const app = express();
    app.locals.db = await database.connect(config.dbPath);

    app.use(express.json());
    app.use(routes);
    app.use(errorHandler);

    if (!config.adminToken) logger.warn('ADMIN_TOKEN not set: admin routes will reject every request');

    app.listen(config.port, () => logger.info('server started', { port: config.port }));
}

start().catch((err) => {
    logger.error('failed to start', { error: err.message, stack: err.stack });
    process.exit(1);
});
