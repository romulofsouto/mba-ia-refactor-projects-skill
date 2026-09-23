const checkoutService = require('../services/checkoutService');

const ERROR_STATUS = { COURSE_NOT_FOUND: 404, PAYMENT_DENIED: 400 };

function parsePayload(body) {
    const { usr, eml, pwd, c_id: courseId, card } = body ?? {};
    const isNonEmptyString = (v) => typeof v === 'string' && v.trim() !== '';

    if (![usr, eml, pwd, card].every(isNonEmptyString)) return null;
    if (!eml.includes('@')) return null;
    if (!/^\d{12,19}$/.test(card)) return null;
    if (!Number.isInteger(Number(courseId)) || Number(courseId) <= 0) return null;

    return { name: usr, email: eml, password: pwd, courseId: Number(courseId), cardNumber: card };
}

async function checkout(req, res) {
    const input = parsePayload(req.body);
    if (!input) return res.status(400).send('Bad Request');

    try {
        const { enrollmentId } = await checkoutService.checkout(req.app.locals.db, input);
        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    } catch (err) {
        if (err instanceof checkoutService.CheckoutError) {
            return res.status(ERROR_STATUS[err.code]).send(err.message);
        }
        throw err;
    }
}

module.exports = { checkout };
