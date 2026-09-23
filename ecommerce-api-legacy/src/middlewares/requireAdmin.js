const crypto = require('crypto');
const { adminToken } = require('../config');

function tokensMatch(provided, expected) {
    const a = Buffer.from(provided);
    const b = Buffer.from(expected);
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Fails closed: without ADMIN_TOKEN configured, admin routes are unreachable.
function requireAdmin(req, res, next) {
    const provided = req.get('X-Admin-Token');
    if (!adminToken || !provided || !tokensMatch(provided, adminToken)) {
        return res.status(401).send('Unauthorized');
    }
    next();
}

module.exports = requireAdmin;
