// Forwards rejected promises from async handlers to the error middleware (Express 4 doesn't).
module.exports = (handler) => (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
