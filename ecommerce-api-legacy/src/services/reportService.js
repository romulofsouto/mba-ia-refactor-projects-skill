const courseModel = require('../models/courseModel');
const { PAID } = require('./paymentGateway');

async function financialReport(db) {
    const rows = await courseModel.findEnrollmentsWithPayments(db);
    const byCourse = new Map();

    for (const row of rows) {
        if (!byCourse.has(row.course_id)) {
            byCourse.set(row.course_id, { course: row.title, revenue: 0, students: [] });
        }
        if (row.enrollment_id === null) continue;

        const entry = byCourse.get(row.course_id);
        if (row.status === PAID) entry.revenue += row.amount;
        entry.students.push({
            student: row.student_name ?? 'Unknown',
            paid: row.amount ?? 0,
        });
    }

    return [...byCourse.values()];
}

module.exports = { financialReport };
