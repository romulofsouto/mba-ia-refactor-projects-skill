const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const paymentGateway = require('./paymentGateway');
const { hashPassword } = require('./passwordHasher');
const logger = require('../config/logger');

class CheckoutError extends Error {
    constructor(code, message) {
        super(message);
        this.code = code;
    }
}

async function checkout(db, { name, email, password, courseId, cardNumber }) {
    const course = await courseModel.findActiveById(db, courseId);
    if (!course) throw new CheckoutError('COURSE_NOT_FOUND', 'Curso não encontrado');

    const status = paymentGateway.charge(cardNumber);
    if (status !== paymentGateway.PAID) throw new CheckoutError('PAYMENT_DENIED', 'Pagamento recusado');

    const { userId, enrollmentId } = await db.transaction(async (tx) => {
        const existing = await userModel.findByEmail(tx, email);
        const userId = existing
            ? existing.id
            : await userModel.create(tx, { name, email, passwordHash: hashPassword(password) });

        const enrollmentId = await enrollmentModel.create(tx, userId, course.id);
        await paymentModel.create(tx, enrollmentId, course.price, status);
        await auditLogModel.record(tx, `Checkout curso ${course.id} por ${userId}`);
        return { userId, enrollmentId };
    });

    logger.info('checkout completed', { userId, courseId: course.id, enrollmentId, card: `****${cardNumber.slice(-4)}` });
    return { enrollmentId };
}

module.exports = { checkout, CheckoutError };
